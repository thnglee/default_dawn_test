"""
Stage 3 — Layout Analysis Agent
Vision-only pass over viewport screenshots → section_map.json
"""

import json

import llm
import skills
from config import MAX_VIEWPORTS
from state import RunState


_TEXT_PROMPT = """
Analyze the provided product page screenshots and return a section_map JSON object.

Each entry in sections[] must include:
- section_id (slug)
- section_type (from the allowed types)
- layout_pattern
- viewport_range [start, end] (0-indexed)
- content_signals []
- confidence (0.0–1.0)
- notes (optional)

Return ONLY valid JSON. No prose.
""".strip()


def run(state: RunState) -> dict:
    """
    Run Layout Analysis Agent on all captured viewport screenshots.
    Returns section_map dict.
    """
    screenshot_paths = state.screenshot_paths()
    if not screenshot_paths:
        raise RuntimeError("No screenshots found — run Stage 1 first")

    # Cap at MAX_VIEWPORTS to control token spend
    paths_to_use = screenshot_paths[:MAX_VIEWPORTS]
    print(f"  → Layout Analysis over {len(paths_to_use)} viewport(s)")

    system = skills.prompt_layout_analysis()
    result = llm.call_vision_json(
        system,
        _TEXT_PROMPT,
        paths_to_use,
        max_tokens=3000,
    )

    # Normalise: agent may return various shapes
    if isinstance(result, list):
        raw_sections = result
    elif isinstance(result, dict) and "sections" in result:
        raw_sections = result["sections"]
    elif isinstance(result, dict) and "section_map" in result:
        raw_sections = result["section_map"]
    elif isinstance(result, dict):
        # Try any list value
        raw_sections = next(
            (v for v in result.values() if isinstance(v, list)), []
        )
    else:
        raw_sections = []

    # Normalise field names (id→section_id, type→section_type, viewport_indices→viewport_range)
    sections = []
    for i, s in enumerate(raw_sections):
        if not isinstance(s, dict):
            continue
        sid = s.get("section_id") or s.get("id") or f"section_{i}"
        stype = s.get("section_type") or s.get("type") or "generic"
        vrange = s.get("viewport_range") or s.get("viewport_indices") or [0, 0]
        sections.append({
            "section_id": sid,
            "section_type": stype,
            "layout_pattern": s.get("layout_pattern", "unknown"),
            "viewport_range": vrange,
            "content_signals": s.get("content_signals", []),
            "confidence": s.get("confidence", 0.8),
            "notes": s.get("notes", ""),
        })

    section_map = {"sections": sections}

    state.write_section_map(section_map)
    section_count = len(section_map.get("sections", []))
    print(f"  ✓ Layout analysis identified {section_count} section(s)")
    return section_map
