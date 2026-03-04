"""
Shopify Page Cloning Pipeline — CLI entry point

Usage:
    python main.py --url https://competitor.com/products/xyz
    python main.py --url https://competitor.com/products/xyz --screenshots shot1.png shot2.png
    python main.py --screenshots figma_frame1.png figma_frame2.png
    python main.py --resume 20240101_120000
    python main.py --url https://... --dev-store-url https://mystore.myshopify.com/products/xyz
"""

import argparse
import sys
import traceback
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def _header(text: str, stage: int) -> None:
    console.rule(f"[bold cyan]Stage {stage} — {text}[/bold cyan]")


def _success(msg: str) -> None:
    console.print(f"[bold green]✓[/bold green] {msg}")


def _error(msg: str) -> None:
    console.print(f"[bold red]✗[/bold red] {msg}")


def _warn(msg: str) -> None:
    console.print(f"[bold yellow]⚠[/bold yellow] {msg}")


def _print_summary(state) -> None:
    """Print pipeline summary table."""
    try:
        summary = state.read("pipeline_summary.json")
    except FileNotFoundError:
        return

    table = Table(title="Pipeline Summary", show_header=True)
    table.add_column("Section", style="cyan")
    table.add_column("Compliance", justify="right")
    table.add_column("Regression", justify="right")
    table.add_column("Status")

    for item in summary.get("sections", []):
        sid = item.get("section_id", "?")
        score = item.get("compliance_score")
        score_str = f"{score:.2f}" if score is not None else "—"
        regression = item.get("regression_decision", "—")
        status = "✓" if item.get("ok") else "⚠"
        table.add_row(sid, score_str, regression, status)

    console.print(table)
    console.print(f"\n[bold]Run ID:[/bold] {state.run_id}")
    console.print(f"[bold]Output dir:[/bold] {state.run_dir}")


def run_pipeline(args: argparse.Namespace) -> int:
    """Execute the full pipeline. Returns exit code."""
    import config  # validate env vars on import

    from state import RunState
    from stages import (
        s1_capture,
        s2_product_sanity,
        s3_layout_analysis,
        s4_app_detection,
        s5_section_conversion,
        s6_dawn_compliance,
        s7_assembly,
        s8_visual_regression,
    )

    # ── State ──────────────────────────────────────────────────────────────
    if args.resume:
        state = RunState.load(args.resume)
        console.print(Panel(f"Resuming run: [bold]{args.resume}[/bold]", style="blue"))
    else:
        state = RunState.create_new()
        console.print(Panel(
            f"Starting new run: [bold]{state.run_id}[/bold]\n"
            f"Input: {args.url or 'screenshots only'}",
            style="blue",
        ))

    extra_screenshots = [Path(p) for p in (args.screenshots or [])]

    # ── Stage 1: Capture ──────────────────────────────────────────────────
    if not state.exists("normalized_page.json") or args.force:
        _header("Page Capture", 1)
        if args.url:
            s1_capture.run(state, args.url, extra_screenshots or None)
        elif extra_screenshots:
            s1_capture.run_from_screenshots(state, extra_screenshots)
        else:
            _error("Provide --url or --screenshots")
            return 1
        _success("Capture complete")
    else:
        console.print("  [dim]Stage 1 skipped (already captured)[/dim]")

    # ── Stage 2: Product Sanity ───────────────────────────────────────────
    if not state.exists("sanity_report.json") or args.force:
        _header("Product Data Sanity", 2)
        try:
            s2_product_sanity.run(state)
            _success("Product sanity passed")
        except RuntimeError as e:
            _error(f"Product sanity BLOCKING error: {e}")
            _error("Pipeline halted. Fix the product data and retry with --resume.")
            return 1
    else:
        console.print("  [dim]Stage 2 skipped (already run)[/dim]")

    # ── Stage 3: Layout Analysis ──────────────────────────────────────────
    if not state.exists("section_map.json") or args.force:
        _header("Layout Analysis", 3)
        s3_layout_analysis.run(state)
        _success("Layout analysis complete")
    else:
        console.print("  [dim]Stage 3 skipped (already run)[/dim]")

    # ── Stage 4: App Detection ────────────────────────────────────────────
    if not state.exists("app_classification.json") or args.force:
        _header("App Detection", 4)
        s4_app_detection.run(state)
        _success("App detection complete")
    else:
        console.print("  [dim]Stage 4 skipped (already run)[/dim]")

    # ── Stage 5: Section Conversion ───────────────────────────────────────
    if not state.exists("sections_draft.json") or args.force:
        _header("Section Conversion", 5)
        s5_section_conversion.run(state)
        _success("Section conversion complete")
    else:
        console.print("  [dim]Stage 5 skipped (already run)[/dim]")

    # ── Stage 6: Dawn Compliance ──────────────────────────────────────────
    if not state.exists("compliance_report.json") or args.force:
        _header("Dawn Compliance", 6)
        s6_dawn_compliance.run(state)
        _success("Compliance check complete")
    else:
        console.print("  [dim]Stage 6 skipped (already run)[/dim]")

    # ── Stage 7: Assembly ─────────────────────────────────────────────────
    _header("Assembly", 7)
    s7_assembly.run(state)
    _success("Assembly complete — sections written to repo")

    # ── Stage 8: Visual Regression ────────────────────────────────────────
    if not args.skip_regression:
        _header("Visual Regression", 8)
        s8_visual_regression.run(
            state,
            dev_store_url=args.dev_store_url,
            shopify_store=args.shopify_store,
        )
        _success("Visual regression complete")
    else:
        _warn("Visual regression skipped (--skip-regression)")

    # ── Summary ───────────────────────────────────────────────────────────
    _write_summary(state)
    _print_summary(state)
    return 0


def _write_summary(state) -> None:
    """Build and write pipeline_summary.json."""
    import json

    try:
        section_map = state.read_section_map()
        compliance = state.read_compliance_report() if state.exists("compliance_report.json") else {}
        regression = state.read_regression_report() if state.exists("regression_report.json") else {}
    except Exception:
        return

    reg_lookup = {
        sec.get("section_id"): sec.get("decision", "—")
        for sec in regression.get("sections", [])
    }

    sections_summary = []
    for sec in section_map.get("sections", []):
        sid = sec.get("section_id")
        comp = compliance.get(sid, {})
        score = comp.get("final_score")
        reg = reg_lookup.get(sid, "—")
        ok = (
            (score is None or score >= 0.7)
            and reg not in ("re_convert", "manual_review")
        )
        sections_summary.append({
            "section_id": sid,
            "section_type": sec.get("section_type"),
            "compliance_score": score,
            "compliance_passes": comp.get("passes_run"),
            "escalated": comp.get("escalated", False),
            "regression_decision": reg,
            "ok": ok,
        })

    state.write_summary({
        "run_id": state.run_id,
        "sections": sections_summary,
        "total": len(sections_summary),
        "ok": sum(1 for s in sections_summary if s["ok"]),
    })


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Clone a competitor Shopify product page into Dawn theme sections.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument(
        "--url", "-u",
        help="Competitor product page URL to capture",
    )
    input_group.add_argument(
        "--resume",
        metavar="RUN_ID",
        help="Resume an existing run by its ID (e.g. 20240101_120000)",
    )

    parser.add_argument(
        "--screenshots", "-s",
        nargs="+",
        metavar="PNG",
        help="Additional screenshot paths (Figma exports or manual captures)",
    )
    parser.add_argument(
        "--dev-store-url",
        help="Full URL to a product on your Shopify dev store (for visual regression)",
    )
    parser.add_argument(
        "--shopify-store",
        help="Shopify store domain (e.g. mystore.myshopify.com) for theme push",
    )
    parser.add_argument(
        "--skip-regression",
        action="store_true",
        help="Skip Stage 8 visual regression",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run all stages even if artifacts already exist",
    )

    args = parser.parse_args()

    if not args.url and not args.screenshots and not args.resume:
        parser.error("Provide --url, --screenshots, or --resume")

    try:
        return run_pipeline(args)
    except KeyboardInterrupt:
        _warn("Interrupted by user")
        return 130
    except Exception:
        console.print_exception()
        return 1


if __name__ == "__main__":
    sys.exit(main())
