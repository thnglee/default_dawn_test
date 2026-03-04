"""
Stage 7 — Assembly
1. Copies final .liquid files to repo sections/
2. Builds templates/product.json wiring all native sections
3. Runs `shopify theme check` for syntax validation

Outputs: sections written to repo, templates/product.json updated
"""

import json
import shutil
import subprocess
from pathlib import Path

from config import SECTIONS_OUT, TEMPLATES_OUT
from state import RunState


_PRODUCT_TEMPLATE_SKELETON = {
    "sections": {},
    "order": [],
}


def _build_product_template(section_ids: list[str], section_map_sections: list[dict]) -> dict:
    """
    Build a templates/product.json that loads all native sections in layout order.
    """
    template = {
        "sections": {},
        "order": [],
    }

    for section in section_map_sections:
        sid = section.get("section_id")
        if sid not in section_ids:
            continue
        template["sections"][sid] = {
            "type": sid,
            "settings": {},
            "blocks": {},
            "block_order": [],
        }
        template["order"].append(sid)

    return template


def run(state: RunState) -> dict:
    """
    Assemble final output into the repo.
    Returns a summary dict of what was written.
    """
    section_map = state.read_section_map()
    sections = section_map.get("sections", [])

    liquid_paths = state.section_liquid_paths()
    if not liquid_paths:
        raise RuntimeError("No .liquid files found — run Stages 5 & 6 first")

    SECTIONS_OUT.mkdir(parents=True, exist_ok=True)
    TEMPLATES_OUT.mkdir(parents=True, exist_ok=True)

    written_sections: list[str] = []
    for liq_path in liquid_paths:
        dest = SECTIONS_OUT / liq_path.name
        shutil.copy2(liq_path, dest)
        written_sections.append(liq_path.stem)
        print(f"    → sections/{liq_path.name}")

    # Build product template
    template_data = _build_product_template(written_sections, sections)
    template_path = TEMPLATES_OUT / "product.json"

    # Merge with existing template if present (preserve header/footer/seo sections)
    if template_path.exists():
        existing = json.loads(template_path.read_text(encoding="utf-8"))
        # Keep existing sections that are not being replaced
        for sid, sdata in existing.get("sections", {}).items():
            if sid not in template_data["sections"]:
                template_data["sections"][sid] = sdata
                # Insert at beginning (header/nav usually comes first)
                if sid not in template_data["order"]:
                    template_data["order"].insert(0, sid)

    template_path.write_text(
        json.dumps(template_data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"    → templates/product.json ({len(template_data['order'])} section(s))")

    # Run shopify theme check
    check_result = _run_theme_check()

    summary = {
        "sections_written": written_sections,
        "template_sections_order": template_data["order"],
        "theme_check": check_result,
    }

    print(f"  ✓ Assembly complete: {len(written_sections)} section(s) written")
    return summary


def _run_theme_check() -> dict:
    """Run `shopify theme check` and return parsed summary."""
    try:
        result = subprocess.run(
            ["shopify", "theme", "check", "--output", "json"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.stdout:
            try:
                data = json.loads(result.stdout)
                errors = [
                    e for e in data if e.get("severity") in ("error", "ERROR")
                ]
                warnings = [
                    e for e in data if e.get("severity") in ("warning", "WARNING")
                ]
                print(f"    theme check: {len(errors)} error(s), {len(warnings)} warning(s)")
                return {"errors": errors, "warnings": warnings, "raw": data}
            except json.JSONDecodeError:
                pass
        # Non-JSON output
        print(f"    theme check exit code: {result.returncode}")
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout[:500],
            "stderr": result.stderr[:200],
        }
    except FileNotFoundError:
        print("    ⚠ shopify CLI not found — skipping theme check")
        return {"skipped": True, "reason": "shopify CLI not found"}
    except subprocess.TimeoutExpired:
        print("    ⚠ theme check timed out")
        return {"skipped": True, "reason": "timeout"}
