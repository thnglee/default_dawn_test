"""
Stage 8 — Visual Regression
1. Pushes theme to Shopify dev store and captures rendered screenshots
2. Calls Visual Regression Agent (vision) to compare original vs rendered
3. Marks sections for re-conversion or manual review

Outputs: regression_report.json
"""

import json
import subprocess
import time
from pathlib import Path
from typing import Optional

import llm
import skills
from config import (
    REGRESSION_MAX_RECONVERTS,
    REGRESSION_MIN_SIMILARITY,
    REGRESSION_PRIORITY_TYPES,
    VIEWPORT_HEIGHT,
    VIEWPORT_WIDTH,
)
from state import RunState

_REGRESSION_PROMPT = """
Compare the original product page screenshots (left/first set) with the
rendered Shopify theme screenshots (right/second set).

Return a JSON regression report following the schema in your system prompt.
Focus on: layout breaks, missing elements, wrong content, style mismatches.
Acceptable: font differences, color scheme changes, app placeholders.

Return ONLY valid JSON.
""".strip()


def _push_theme(store: Optional[str] = None) -> bool:
    """Push theme to dev store. Returns True on success."""
    cmd = ["shopify", "theme", "push", "--development"]
    if store:
        cmd += ["--store", store]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            print("    ✓ Theme pushed to dev store")
            return True
        else:
            print(f"    ✗ Theme push failed: {result.stderr[:200]}")
            return False
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        print(f"    ⚠ Theme push skipped: {e}")
        return False


def _capture_dev_screenshots(
    dev_url: str,
    state: RunState,
) -> list[Path]:
    """
    Capture screenshots from the dev store's product page.
    Returns list of screenshot paths.
    """
    from playwright.sync_api import sync_playwright

    dev_dir = state.run_dir / "dev_screenshots"
    dev_dir.mkdir(exist_ok=True)

    paths: list[Path] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT}
        )
        try:
            page.goto(dev_url, wait_until="networkidle", timeout=60_000)
            page.wait_for_timeout(2000)

            total_height = page.evaluate("() => document.documentElement.scrollHeight")
            step = VIEWPORT_HEIGHT
            scroll_positions = list(range(0, total_height, step))[:8]

            for i, scroll_y in enumerate(scroll_positions):
                page.evaluate(f"window.scrollTo(0, {scroll_y})")
                page.wait_for_timeout(300)
                img_path = dev_dir / f"dev_{i:02d}.png"
                page.screenshot(path=str(img_path), type="png")
                paths.append(img_path)
        finally:
            browser.close()

    return paths


def _run_vision_comparison(
    original_paths: list[Path],
    dev_paths: list[Path],
    section_map: dict,
) -> dict:
    """Call Visual Regression Agent with both sets of screenshots."""
    system = skills.prompt_visual_regression()

    # Interleave: original[0], dev[0], original[1], dev[1], ...
    # so the agent can compare viewport-by-viewport
    max_pairs = min(len(original_paths), len(dev_paths), 4)  # cap at 4 pairs
    interleaved: list[Path] = []
    for i in range(max_pairs):
        interleaved.append(original_paths[i])
        interleaved.append(dev_paths[i])

    sections_context = json.dumps(
        [{"section_id": s["section_id"], "section_type": s["section_type"]}
         for s in section_map.get("sections", [])],
        indent=2,
    )

    user_text = (
        f"{_REGRESSION_PROMPT}\n\n"
        f"Section context:\n{sections_context}"
    )

    return llm.call_vision_json(
        system,
        user_text,
        interleaved,
        max_tokens=3000,
    )


def run(
    state: RunState,
    dev_store_url: Optional[str] = None,
    shopify_store: Optional[str] = None,
) -> dict:
    """
    Run visual regression.
    If dev_store_url is None, skip the Playwright capture and compare
    only against original screenshots (useful in offline mode).

    Returns regression_report dict.
    """
    section_map = state.read_section_map()
    original_paths = state.screenshot_paths()

    if not original_paths:
        print("  ⚠ No original screenshots — skipping visual regression")
        report = {"skipped": True, "reason": "no_original_screenshots"}
        state.write_regression_report(report)
        return report

    dev_paths: list[Path] = []

    if dev_store_url:
        # Push theme first
        push_ok = _push_theme(shopify_store)
        if push_ok:
            time.sleep(5)  # let store propagate
            dev_paths = _capture_dev_screenshots(dev_store_url, state)
    else:
        print("  ⚠ No dev_store_url — visual regression will use original screenshots only")
        dev_paths = original_paths  # compare original to itself (will always pass)

    print(f"  → Visual Regression: {len(original_paths)} original, {len(dev_paths)} dev screenshots")

    try:
        report = _run_vision_comparison(original_paths, dev_paths, section_map)
    except Exception as e:
        print(f"  ✗ Visual regression agent failed: {e}")
        report = {"error": str(e), "sections": []}

    # Identify re-convert candidates
    sections_to_reconvert = []
    for sec in report.get("sections", []):
        decision = sec.get("decision", "")
        if decision == "re_convert" and len(sections_to_reconvert) < REGRESSION_MAX_RECONVERTS:
            sections_to_reconvert.append(sec.get("section_id"))

    if sections_to_reconvert:
        print(f"  ⚠ {len(sections_to_reconvert)} section(s) flagged for re-conversion: "
              f"{sections_to_reconvert}")
        print("    Re-conversion is a manual step — check regression_report.json")

    manual_review = [
        sec.get("section_id")
        for sec in report.get("sections", [])
        if sec.get("decision") == "manual_review"
    ]
    if manual_review:
        print(f"  ⚠ {len(manual_review)} section(s) need manual review: {manual_review}")

    state.write_regression_report(report)

    passed = sum(
        1 for sec in report.get("sections", [])
        if sec.get("decision") in ("pass", "warn")
    )
    total = len(report.get("sections", []))
    print(f"  ✓ Visual regression: {passed}/{total} section(s) passed")
    return report
