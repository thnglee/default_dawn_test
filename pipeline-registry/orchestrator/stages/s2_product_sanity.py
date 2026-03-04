"""
Stage 2 — Product Data Sanity Agent
Validates extracted product data and produces product_liquid_map.json.
Pipeline halts if valid=false and any blocking error exists.
"""

import json

import llm
import skills
from state import RunState


def _extract_product_data(normalized_page: dict) -> dict:
    """Pull product data from pre-built product_data, JSON-LD, and meta tags."""
    product_data: dict = {
        "title": None,
        "vendor": None,
        "type": None,
        "description": None,
        "price": None,
        "compare_at_price": None,
        "variants": [],
        "options": [],
        "images": [],
    }

    # Pre-built product_data (from Shopify .js endpoint in Stage 1)
    prebuilt = normalized_page.get("product_data")
    if prebuilt and isinstance(prebuilt, dict):
        product_data.update({k: v for k, v in prebuilt.items() if v is not None})
        if product_data.get("variants") and product_data.get("price"):
            return product_data  # complete data, skip JSON-LD / meta

    # JSON-LD product schema
    for ld in normalized_page.get("json_ld", []):
        if isinstance(ld, dict) and ld.get("@type") in ("Product", "product"):
            product_data["title"] = ld.get("name")
            product_data["description"] = ld.get("description")
            product_data["vendor"] = ld.get("brand", {}).get("name") if isinstance(ld.get("brand"), dict) else ld.get("brand")

            offers = ld.get("offers", [])
            if isinstance(offers, dict):
                offers = [offers]
            for offer in offers:
                price_raw = offer.get("price")
                if price_raw is not None:
                    try:
                        price_cents = int(float(str(price_raw).replace(",", "")) * 100)
                        product_data["price"] = price_cents
                    except (ValueError, TypeError):
                        pass

            images = ld.get("image", [])
            if isinstance(images, str):
                images = [images]
            product_data["images"] = [{"src": img, "alt": None} for img in images]
            break

    # Meta tags fallback
    meta = normalized_page.get("meta", {})
    if not product_data["title"]:
        product_data["title"] = (
            meta.get("og:title") or meta.get("twitter:title")
        )
    if not product_data["description"]:
        product_data["description"] = (
            meta.get("og:description") or meta.get("description")
        )
    if not product_data["images"] and meta.get("og:image"):
        product_data["images"] = [{"src": meta["og:image"], "alt": None}]

    return product_data


def run(state: RunState) -> dict:
    """
    Run the Product Data Sanity Agent.
    Returns the full agent output (valid, product_liquid_map, errors, warnings).
    Raises RuntimeError if blocking errors prevent pipeline continuation.
    """
    normalized_page = state.read_normalized_page()
    product_data = _extract_product_data(normalized_page)

    print(f"  → Running Product Sanity Agent (title: {product_data.get('title')!r})")

    system = skills.prompt_product_sanity()
    user_text = json.dumps({
        "raw_product_data": product_data,
        "source_url": normalized_page.get("url"),
    }, indent=2)

    result = llm.call_json(system, user_text, max_tokens=1500)

    state.write_product_liquid_map(result.get("product_liquid_map", {}))
    state.write_sanity_report(result)

    # Check blocking errors
    errors = result.get("errors", [])
    blocking = [e for e in errors if e.get("blocking")]
    if not result.get("valid", True) and blocking:
        msg = "; ".join(e.get("issue", "unknown") for e in blocking)
        raise RuntimeError(f"Product sanity blocking error(s): {msg}")

    warnings = result.get("warnings", [])
    if warnings:
        print(f"  ⚠ {len(warnings)} sanity warning(s): "
              + ", ".join(w.get("field", "?") for w in warnings))

    print(f"  ✓ Product sanity passed (valid={result.get('valid')})")
    return result
