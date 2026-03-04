"""
Load skill markdown files and inject them into agent system prompts.
Skills are static files — no LLM involved in loading them.
"""

from pathlib import Path
from config import SKILLS_DIR, PROMPTS_DIR


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ── Skills ───────────────────────────────────────────────────────────────────

def skill_html_to_liquid() -> str:
    return _read(SKILLS_DIR / "html_to_liquid.md")


def skill_dawn_conventions() -> str:
    return _read(SKILLS_DIR / "dawn_conventions.md")


def skill_accessibility() -> str:
    return _read(SKILLS_DIR / "accessibility_enforcement.md")


def skill_app_placeholder_template() -> str:
    return _read(SKILLS_DIR / "app_placeholder.liquid.tpl")


# ── Agent prompts ─────────────────────────────────────────────────────────────

def prompt_layout_analysis() -> str:
    return _read(PROMPTS_DIR / "layout_analysis.txt")


def prompt_app_detection() -> str:
    return _read(PROMPTS_DIR / "app_detection.txt")


def prompt_product_sanity() -> str:
    return _read(PROMPTS_DIR / "product_sanity.txt")


def prompt_section_conversion() -> str:
    """Section conversion system prompt with all three skills injected."""
    base = _read(PROMPTS_DIR / "section_conversion.txt")
    skills_block = "\n\n".join([
        "## INJECTED SKILL: html_to_liquid\n" + skill_html_to_liquid(),
        "## INJECTED SKILL: dawn_conventions\n" + skill_dawn_conventions(),
        "## INJECTED SKILL: accessibility_enforcement\n" + skill_accessibility(),
    ])
    return base + "\n\n---\n\n" + skills_block


def prompt_dawn_compliance() -> str:
    base = _read(PROMPTS_DIR / "dawn_compliance.txt")
    return base + "\n\n---\n\n## INJECTED SKILL: dawn_conventions\n" + skill_dawn_conventions()


def prompt_visual_regression() -> str:
    return _read(PROMPTS_DIR / "visual_regression.txt")
