"""
Stage 4 — App Detection
1. Deterministic fingerprint match from app_signatures.json
2. LLM fallback for unknown apps
3. Placeholder generation for confirmed apps

Outputs: app_classification.json (list of per-section results)
"""

import json
import re
from pathlib import Path

import llm
import skills
from config import FINGERPRINTS
from state import RunState


# ── load fingerprints ─────────────────────────────────────────────────────────

def _load_signatures() -> dict:
    return json.loads(FINGERPRINTS.read_text(encoding="utf-8"))


# ── deterministic matcher ─────────────────────────────────────────────────────

def _fingerprint_match(section_dom: dict, signatures: dict) -> dict | None:
    """
    Returns the matching signature entry or None.
    Checks classes, data_attributes, ids, scripts, iframe_src_patterns.
    """
    html = section_dom.get("html_snippet", "")
    class_list = section_dom.get("class_list", "")
    data_attrs = section_dom.get("data_attributes", {})
    script_refs = section_dom.get("script_refs", [])

    allowlist: list[str] = signatures.get("_allowlist", {}).get("dawn_native_classes", [])

    for category, apps in signatures.items():
        if category.startswith("_"):
            continue
        # categories are dicts keyed by slug → iterate values
        app_iter = apps.values() if isinstance(apps, dict) else apps
        for app in app_iter:
            # classes
            for cls in app.get("classes", []):
                if cls in class_list and cls not in allowlist:
                    return app

            # data_attributes
            for attr in app.get("data_attributes", []):
                if attr in data_attrs:
                    return app

            # ids
            for id_val in app.get("ids", []):
                if f'id="{id_val}"' in html or f"id='{id_val}'" in html:
                    return app

            # scripts
            for script_pattern in app.get("scripts", []):
                for ref in script_refs:
                    if script_pattern in ref:
                        return app

            # iframe src patterns
            if section_dom.get("has_iframe"):
                for pattern in app.get("iframe_src_patterns", []):
                    if re.search(pattern, html):
                        return app

    # iframe with no known pattern → still an app
    if section_dom.get("has_iframe"):
        return {
            "app_name": "Unknown App (iframe)",
            "app_slug": "unknown-app-iframe",
            "placeholder_type": "generic",
            "merchant_instruction": (
                "This section is rendered by a third-party app via an iframe. "
                "Re-install the app and configure it to display here."
            ),
            "app_store_url": None,
        }

    return None


# ── LLM fallback ──────────────────────────────────────────────────────────────

def _llm_classify(section_id: str, section_dom: dict) -> dict:
    system = skills.prompt_app_detection()
    payload = {
        "section_id": section_id,
        "class_list": section_dom.get("class_list", ""),
        "data_attributes": section_dom.get("data_attributes", {}),
        "html_snippet": section_dom.get("html_snippet", "")[:1500],
        "content_signals": section_dom.get("content_signals", []),
        "has_iframe": section_dom.get("has_iframe", False),
        "script_refs": section_dom.get("script_refs", []),
    }
    return llm.call_json(system, json.dumps(payload, indent=2), max_tokens=600)


# ── main ──────────────────────────────────────────────────────────────────────

def run(state: RunState) -> list[dict]:
    """
    Classify each section as app or non-app.
    Returns list of classification results.
    """
    section_map = state.read_section_map()
    normalized_page = state.read_normalized_page()
    sections = section_map.get("sections", [])
    dom_sections = normalized_page.get("sections_dom", [])

    # Build a quick lookup: section_type/section_id → dom entry by position
    # (Layout analysis identifies by viewport position; we match by index order)
    signatures = _load_signatures()
    results: list[dict] = []

    llm_calls = 0
    fingerprint_hits = 0
    non_app_count = 0

    for i, section in enumerate(sections):
        section_id = section.get("section_id", f"section_{i}")
        section_type = section.get("section_type", "unknown")

        # Only run app detection on sections that could plausibly be apps
        # (skip product_info, product_gallery — these are always native)
        if section_type in {"product_info", "product_gallery"}:
            results.append({
                "section_id": section_id,
                "is_app": False,
                "detection_method": "skipped_native_type",
                "confidence": 1.0,
                "app_name": None,
                "app_slug": None,
                "evidence": [f"Section type '{section_type}' is always Shopify-native"],
                "placeholder_config": None,
            })
            non_app_count += 1
            continue

        # Get corresponding DOM entry (best effort, by position)
        dom = dom_sections[i] if i < len(dom_sections) else {}

        # 1. Fingerprint match
        match = _fingerprint_match(dom, signatures)
        if match:
            fingerprint_hits += 1
            results.append({
                "section_id": section_id,
                "is_app": True,
                "detection_method": "fingerprint",
                "confidence": 0.99,
                "app_name": match.get("app_name") or match.get("name"),
                "app_slug": match.get("app_slug") or match.get("slug"),
                "evidence": ["Fingerprint match on class/attr/iframe"],
                "placeholder_config": {
                    "type": match.get("placeholder_type", "generic"),
                    "liquid_block_name": f"app-placeholder-{match.get('app_slug') or match.get('slug', section_id)}",
                    "merchant_instruction": match.get("merchant_instruction", ""),
                    "app_store_url": match.get("app_store_url"),
                },
            })
            continue

        # 2. LLM fallback (only if there are suspicious signals)
        suspicious = (
            dom.get("has_iframe")
            or any("star" in s or "review" in s or "bundle" in s or "quiz" in s
                   for s in dom.get("content_signals", []))
            or len(dom.get("script_refs", [])) > 0
        )

        if suspicious and dom:
            llm_calls += 1
            try:
                llm_result = _llm_classify(section_id, dom)
                results.append(llm_result)
                if llm_result.get("is_app"):
                    continue  # will be handled as app
            except Exception as e:
                print(f"    ⚠ LLM app detection failed for {section_id}: {e}")

        results.append({
            "section_id": section_id,
            "is_app": False,
            "detection_method": "no_signals",
            "confidence": 0.85,
            "app_name": None,
            "app_slug": None,
            "evidence": ["No app fingerprints or suspicious signals detected"],
            "placeholder_config": None,
        })
        non_app_count += 1

    state.write_app_classification(results)

    app_count = sum(1 for r in results if r.get("is_app"))
    print(f"  ✓ App detection complete: {app_count} app(s), {non_app_count} native "
          f"({fingerprint_hits} fingerprint, {llm_calls} LLM)")
    return results
