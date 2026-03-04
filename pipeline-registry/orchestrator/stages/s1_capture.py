"""
Stage 1 — Page Capture
Captures viewport screenshots, extracts DOM snippets, JSON-LD, and meta tags
from a competitor product page URL.

Outputs: normalized_page.json + viewport_*.png screenshots
"""

import json
import re
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests

from config import (
    MAX_HTML_SNIPPET_CHARS,
    MAX_VIEWPORTS,
    VIEWPORT_HEIGHT,
    VIEWPORT_WIDTH,
)
from state import RunState


def run(state: RunState, url: str, extra_screenshots: Optional[list[Path]] = None) -> dict:
    """
    Capture the page at `url`.
    If `extra_screenshots` are provided (e.g. from Figma MCP), they are
    copied into the run's screenshots dir and supplement the Playwright capture.

    Returns the normalized_page dict.
    """
    from playwright.sync_api import sync_playwright

    page_data: dict = {
        "url": url,
        "json_ld": [],
        "meta": {},
        "sections_dom": [],
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT})

        print(f"  → Loading {url}")
        page.goto(url, wait_until="networkidle", timeout=60_000)
        page.wait_for_timeout(2000)  # allow JS hydration

        # ── JSON-LD extraction ─────────────────────────────────────────────
        json_ld_raw = page.evaluate("""
            () => Array.from(
                document.querySelectorAll('script[type="application/ld+json"]')
            ).map(s => s.textContent)
        """)
        for raw in json_ld_raw:
            try:
                page_data["json_ld"].append(json.loads(raw))
            except json.JSONDecodeError:
                pass

        # ── Meta tags ─────────────────────────────────────────────────────
        meta_raw = page.evaluate("""
            () => {
                const out = {};
                document.querySelectorAll('meta').forEach(m => {
                    const name = m.getAttribute('name') || m.getAttribute('property');
                    const content = m.getAttribute('content');
                    if (name && content) out[name] = content;
                });
                return out;
            }
        """)
        page_data["meta"] = meta_raw

        # ── Scroll screenshots ─────────────────────────────────────────────
        total_height = page.evaluate("() => document.documentElement.scrollHeight")
        step = VIEWPORT_HEIGHT
        scroll_positions = list(range(0, total_height, step))[:MAX_VIEWPORTS]

        for i, scroll_y in enumerate(scroll_positions):
            page.evaluate(f"window.scrollTo(0, {scroll_y})")
            page.wait_for_timeout(300)
            img_path = state.screenshots_dir / f"viewport_{i:02d}.png"
            page.screenshot(path=str(img_path), type="png")

        # ── DOM section extraction ────────────────────────────────────────
        sections_raw = page.evaluate(f"""
            () => {{
                const MAX_CHARS = {MAX_HTML_SNIPPET_CHARS};
                const candidates = document.querySelectorAll(
                    'section, [class*="section"], [class*="block"], ' +
                    '[class*="hero"], [class*="product"], [class*="feature"], ' +
                    '[class*="banner"], [class*="reviews"], [class*="faq"], ' +
                    '[class*="trust"], [class*="tab"]'
                );

                const seen = new Set();
                const results = [];

                for (const el of candidates) {{
                    // Skip if it's a child of an already-captured element
                    let dominated = false;
                    for (const existing of results) {{
                        if (existing._el && existing._el.contains(el)) {{
                            dominated = true;
                            break;
                        }}
                    }}
                    if (dominated) continue;

                    const html = el.outerHTML;
                    if (!html || seen.has(el)) continue;

                    seen.add(el);

                    const rect = el.getBoundingClientRect();
                    const classList = Array.from(el.classList).join(' ');
                    const dataAttrs = {{}};
                    for (const attr of el.attributes) {{
                        if (attr.name.startsWith('data-')) {{
                            dataAttrs[attr.name] = attr.value;
                        }}
                    }}

                    results.push({{
                        tag: el.tagName.toLowerCase(),
                        class_list: classList,
                        data_attributes: dataAttrs,
                        html_snippet: html.slice(0, MAX_CHARS),
                        html_truncated: html.length > MAX_CHARS,
                        rect: {{
                            top: rect.top + window.scrollY,
                            height: rect.height,
                        }},
                        has_iframe: el.querySelector('iframe') !== null,
                        script_refs: Array.from(el.querySelectorAll('script[src]'))
                            .map(s => s.src).slice(0, 5),
                        content_signals: _extractSignals(el),
                    }});
                }}

                return results;

                function _extractSignals(el) {{
                    const signals = [];
                    const text = el.textContent.toLowerCase();
                    if (el.querySelectorAll('img').length > 0) signals.push('has_images');
                    if (el.querySelector('[class*="star"], [class*="rating"]')) signals.push('star_rating');
                    if (text.includes('add to cart') || text.includes('buy now')) signals.push('atc_button');
                    if (text.includes('subscribe') || text.includes('save')) signals.push('subscribe_save');
                    if (text.includes('frequently bought') || text.includes('bundle')) signals.push('bundle');
                    if (text.includes('faq') || text.includes('question')) signals.push('faq');
                    if (el.querySelector('video, [class*="video"]')) signals.push('video');
                    if (el.querySelector('form')) signals.push('form');
                    if (el.querySelectorAll('li, [class*="item"]').length >= 3) signals.push('list_items');
                    if (el.querySelector('iframe')) signals.push('iframe');
                    return signals;
                }}
            }}
        """)

        page_data["sections_dom"] = sections_raw
        browser.close()

    # ── Copy any extra screenshots (Figma frames) ──────────────────────────
    if extra_screenshots:
        existing_count = len(list(state.screenshots_dir.glob("viewport_*.png")))
        for i, src in enumerate(extra_screenshots):
            dst = state.screenshots_dir / f"viewport_{existing_count + i:02d}.png"
            dst.write_bytes(src.read_bytes())

    # ── Shopify product JSON (reliable, no JS needed) ─────────────────────
    page_data["product_data"] = _fetch_shopify_product(url)

    state.write_normalized_page(page_data)
    print(f"  ✓ Captured {len(page_data['sections_dom'])} DOM sections, "
          f"{len(list(state.screenshots_dir.glob('viewport_*.png')))} screenshots")
    return page_data


def _fetch_shopify_product(url: str) -> dict:
    """
    Fetch product JSON from Shopify's /products/handle.js endpoint.
    Returns normalized product_data dict, or empty dict on failure.
    """
    try:
        parsed = urlparse(url)
        # Build .js URL: keep scheme + netloc + path, append .js
        js_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}.js"
        r = requests.get(js_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        if r.status_code != 200:
            return {}
        shopify = r.json()

        def get_img_src(img):
            return img.get("src") if isinstance(img, dict) else str(img)

        return {
            "title": shopify.get("title"),
            "vendor": shopify.get("vendor"),
            "type": shopify.get("product_type"),
            "description": shopify.get("description"),
            "handle": shopify.get("handle"),
            "price": shopify.get("price_min"),
            "compare_at_price": shopify.get("compare_at_price_min"),
            "variants": [
                {
                    "id": v.get("id"),
                    "title": v.get("title"),
                    "price": v.get("price"),
                    "compare_at_price": v.get("compare_at_price"),
                    "sku": v.get("sku"),
                    "available": v.get("available"),
                    "option1": v.get("option1"),
                    "option2": v.get("option2"),
                    "option3": v.get("option3"),
                }
                for v in shopify.get("variants", [])
            ],
            "options": shopify.get("options", []),
            "images": [
                {"src": get_img_src(img), "alt": None}
                for img in shopify.get("images", [])[:8]
            ],
        }
    except Exception as e:
        print(f"  ⚠ Could not fetch Shopify product JSON: {e}")
        return {}


def run_from_screenshots(state: RunState, screenshot_paths: list[Path]) -> dict:
    """
    Screenshot-only mode (no URL). Copies screenshots and creates a minimal
    normalized_page with empty DOM sections (layout_analysis uses vision only).
    """
    for i, src in enumerate(screenshot_paths):
        dst = state.screenshots_dir / f"viewport_{i:02d}.png"
        dst.write_bytes(src.read_bytes())

    page_data = {
        "url": None,
        "json_ld": [],
        "meta": {},
        "sections_dom": [],
    }
    state.write_normalized_page(page_data)
    print(f"  ✓ Loaded {len(screenshot_paths)} screenshots (screenshot-only mode)")
    return page_data
