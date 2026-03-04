"""
Stage 5 — Section Conversion
Converts each non-app section's HTML snippet into a Dawn-compatible .liquid file.
Runs in parallel (ThreadPoolExecutor).

For app sections: generates placeholder .liquid using the template.
Outputs: sections_draft.json + per-section .liquid files in run/sections/
"""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import llm
import skills
from config import CONVERSION_MAX_WORKERS, MAX_HTML_SNIPPET_CHARS
from state import RunState


# ── placeholder generator ─────────────────────────────────────────────────────

def _make_placeholder(section_id: str, app_result: dict) -> str:
    """Render app_placeholder.liquid.tpl with per-app values.
    The template uses {{VARIABLE}} syntax (not Python string.Template).
    """
    tpl_str = skills.skill_app_placeholder_template()
    cfg = app_result.get("placeholder_config") or {}

    replacements = {
        "{{APP_NAME}}": app_result.get("app_name") or "Third-Party App",
        "{{APP_SLUG}}": app_result.get("app_slug") or section_id,
        "{{SECTION_ID}}": section_id,
        "{{MERCHANT_INSTRUCTION}}": cfg.get("merchant_instruction", "Install the required app."),
        "{{APP_STORE_URL}}": cfg.get("app_store_url") or "https://apps.shopify.com",
        "{{PLACEHOLDER_TYPE}}": cfg.get("type", "generic"),
        "{{DETECTION_CONFIDENCE}}": "0.99",
    }

    result = tpl_str
    for placeholder, value in replacements.items():
        result = result.replace(placeholder, str(value))
    return result


# ── section conversion ────────────────────────────────────────────────────────

def _convert_one(
    section: dict,
    dom: dict,
    product_liquid_map: dict,
    system_prompt: str,
) -> tuple[str, str]:
    """
    Convert one section. Returns (section_id, liquid_string).
    Raises on failure.
    """
    section_id = section.get("section_id")

    # Build dawn_schema_template stub for reference
    schema_stub = {
        "name": section_id.replace("_", " ").title(),
        "tag": "section",
        "class": section_id.replace("_", "-"),
    }

    payload = {
        "section_id": section_id,
        "section_type": section.get("section_type"),
        "layout_pattern": section.get("layout_pattern"),
        "html_snippet": (dom.get("html_snippet") or "")[:MAX_HTML_SNIPPET_CHARS],
        "content_signals": section.get("content_signals", []) or dom.get("content_signals", []),
        "product_liquid_map": product_liquid_map,
        "dawn_schema_template": schema_stub,
    }

    liquid = llm.call_section_conversion(system_prompt, payload)
    return section_id, liquid


# ── main ──────────────────────────────────────────────────────────────────────

def run(state: RunState) -> dict:
    """
    Convert all sections. App sections → placeholder. Native sections → LLM.
    Returns sections_draft dict {section_id: liquid_string}.
    """
    section_map = state.read_section_map()
    app_classification = state.read_app_classification()
    product_liquid_map = state.read_product_liquid_map()
    normalized_page = state.read_normalized_page()

    sections = section_map.get("sections", [])
    dom_sections = normalized_page.get("sections_dom", [])

    # Build app lookup
    app_lookup = {r["section_id"]: r for r in app_classification}

    # Separate app vs native sections
    app_sections = []
    native_sections = []
    for i, section in enumerate(sections):
        sid = section.get("section_id", f"section_{i}")
        app_result = app_lookup.get(sid, {})
        dom = dom_sections[i] if i < len(dom_sections) else {}
        if app_result.get("is_app"):
            app_sections.append((section, app_result))
        else:
            native_sections.append((section, dom))

    print(f"  → Converting {len(native_sections)} native + {len(app_sections)} app sections")

    sections_draft: dict[str, str] = {}
    system_prompt = skills.prompt_section_conversion()

    # ── App placeholders (fast, no LLM) ──────────────────────────────────────
    for section, app_result in app_sections:
        sid = section.get("section_id")
        liquid = _make_placeholder(sid, app_result)
        sections_draft[sid] = liquid
        state.write_section_liquid(sid, liquid)

    # ── Native sections (parallel LLM) ───────────────────────────────────────
    failed: list[str] = []

    with ThreadPoolExecutor(max_workers=CONVERSION_MAX_WORKERS) as executor:
        futures = {
            executor.submit(
                _convert_one, section, dom, product_liquid_map, system_prompt
            ): section.get("section_id")
            for section, dom in native_sections
        }

        for future in as_completed(futures):
            sid = futures[future]
            try:
                section_id, liquid = future.result()
                sections_draft[section_id] = liquid
                state.write_section_liquid(section_id, liquid)
                print(f"    ✓ {section_id}")
            except Exception as e:
                print(f"    ✗ {sid}: {e}")
                failed.append(sid)

    state.write_sections_draft(sections_draft)

    if failed:
        print(f"  ⚠ {len(failed)} section(s) failed conversion: {failed}")
    else:
        print(f"  ✓ All {len(sections_draft)} section(s) converted")

    return sections_draft
