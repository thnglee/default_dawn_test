"""
Stage 5 — Section Conversion
Converts each non-app section's HTML snippet into a Dawn-compatible .liquid file
plus a template_data JSON blob with exact cloned content for product.json.
Runs in parallel (ThreadPoolExecutor).

For app sections: generates placeholder .liquid using the template.
Outputs: sections_draft.json + sections_template_data.json + per-section .liquid files
"""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import llm
import skills
from config import CONVERSION_MAX_WORKERS, MAX_HTML_SNIPPET_CHARS
from state import RunState

# Separator between .liquid content and template_data JSON in agent output
_TEMPLATE_DATA_SEPARATOR = "===TEMPLATE_DATA==="


# ── output parsing ────────────────────────────────────────────────────────────

def _parse_conversion_output(raw: str) -> tuple[str, dict]:
    """
    Split agent output into (liquid_string, template_data_dict).
    If the separator is missing, returns empty template_data as fallback.
    """
    if _TEMPLATE_DATA_SEPARATOR in raw:
        parts = raw.split(_TEMPLATE_DATA_SEPARATOR, 1)
        liquid = parts[0].strip()
        try:
            template_data = json.loads(parts[1].strip())
        except (json.JSONDecodeError, IndexError):
            # Try extracting JSON from the remainder
            remainder = parts[1].strip()
            template_data = _extract_json_safe(remainder)
    else:
        liquid = raw.strip()
        template_data = {}

    # Ensure expected keys
    template_data.setdefault("settings", {})
    template_data.setdefault("blocks", {})
    template_data.setdefault("block_order", [])

    return liquid, template_data


def _extract_json_safe(text: str) -> dict:
    """Best-effort JSON extraction from text. Returns {} on failure."""
    text = text.strip()
    # Strip markdown fences
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Find first {
        idx = text.find("{")
        if idx == -1:
            return {}
        depth = 0
        in_str = False
        esc = False
        for i, ch in enumerate(text[idx:], start=idx):
            if esc:
                esc = False
                continue
            if ch == "\\" and in_str:
                esc = True
                continue
            if ch == '"':
                in_str = not in_str
            elif not in_str:
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(text[idx : i + 1])
                        except json.JSONDecodeError:
                            return {}
    return {}


# ── placeholder generator ─────────────────────────────────────────────────────

def _make_placeholder(section_id: str, app_result: dict) -> str:
    """Render app_placeholder.liquid.tpl with per-app values."""
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
) -> tuple[str, str, dict]:
    """
    Convert one section. Returns (section_id, liquid_string, template_data).
    Raises on failure.
    """
    section_id = section.get("section_id")

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

    raw = llm.call_section_conversion(system_prompt, payload)
    liquid, template_data = _parse_conversion_output(raw)
    return section_id, liquid, template_data


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
    template_data_all: dict[str, dict] = {}
    system_prompt = skills.prompt_section_conversion()

    # ── App placeholders (fast, no LLM) ──────────────────────────────────────
    for section, app_result in app_sections:
        sid = section.get("section_id")
        liquid = _make_placeholder(sid, app_result)
        sections_draft[sid] = liquid
        template_data_all[sid] = {"settings": {}, "blocks": {}, "block_order": []}
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
                section_id, liquid, template_data = future.result()
                sections_draft[section_id] = liquid
                template_data_all[section_id] = template_data
                state.write_section_liquid(section_id, liquid)
                block_count = len(template_data.get("blocks", {}))
                setting_count = len(template_data.get("settings", {}))
                print(f"    ✓ {section_id} ({setting_count} settings, {block_count} blocks)")
            except Exception as e:
                print(f"    ✗ {sid}: {e}")
                failed.append(sid)

    state.write_sections_draft(sections_draft)
    state.write_sections_template_data(template_data_all)

    if failed:
        print(f"  ⚠ {len(failed)} section(s) failed conversion: {failed}")
    else:
        print(f"  ✓ All {len(sections_draft)} section(s) converted")

    return sections_draft
