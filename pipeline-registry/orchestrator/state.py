"""
Run state management.
One run = one timestamped directory under pipeline-registry/runs/{run_id}/
All intermediate artifacts are JSON files in that directory.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from config import RUNS_DIR

# Artifact filenames
NORMALIZED_PAGE = "normalized_page.json"
PRODUCT_LIQUID_MAP = "product_liquid_map.json"
SANITY_REPORT = "sanity_report.json"
SECTION_MAP = "section_map.json"
APP_CLASSIFICATION = "app_classification.json"  # list of per-section results
SECTIONS_DRAFT = "sections_draft.json"           # {section_id: liquid_string}
COMPLIANCE_REPORT = "compliance_report.json"     # {section_id: report}
REGRESSION_REPORT = "regression_report.json"
PIPELINE_SUMMARY = "pipeline_summary.json"

SCREENSHOTS_DIR = "screenshots"      # viewport PNGs from capture
SECTIONS_FINAL_DIR = "sections"      # final .liquid files before repo copy


class RunState:
    def __init__(self, run_id: str):
        self.run_id = run_id
        self.run_dir = RUNS_DIR / run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)
        (self.run_dir / SECTIONS_FINAL_DIR).mkdir(exist_ok=True)
        (self.run_dir / SCREENSHOTS_DIR).mkdir(exist_ok=True)

    # ── generic read/write ────────────────────────────────────────────────────

    def write(self, filename: str, data: Any) -> None:
        path = self.run_dir / filename
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def read(self, filename: str) -> Any:
        path = self.run_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Artifact not found: {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    def exists(self, filename: str) -> bool:
        return (self.run_dir / filename).exists()

    # ── screenshots ───────────────────────────────────────────────────────────

    @property
    def screenshots_dir(self) -> Path:
        return self.run_dir / SCREENSHOTS_DIR

    def screenshot_paths(self) -> list[Path]:
        return sorted(self.screenshots_dir.glob("viewport_*.png"))

    # ── sections final dir ────────────────────────────────────────────────────

    @property
    def sections_final_dir(self) -> Path:
        return self.run_dir / SECTIONS_FINAL_DIR

    def write_section_liquid(self, section_id: str, liquid: str) -> Path:
        path = self.sections_final_dir / f"{section_id}.liquid"
        path.write_text(liquid, encoding="utf-8")
        return path

    def read_section_liquid(self, section_id: str) -> str:
        path = self.sections_final_dir / f"{section_id}.liquid"
        return path.read_text(encoding="utf-8")

    def section_liquid_paths(self) -> list[Path]:
        return sorted(self.sections_final_dir.glob("*.liquid"))

    # ── typed helpers (read/write specific artifacts) ─────────────────────────

    def write_normalized_page(self, data: dict) -> None:
        self.write(NORMALIZED_PAGE, data)

    def read_normalized_page(self) -> dict:
        return self.read(NORMALIZED_PAGE)

    def write_product_liquid_map(self, data: dict) -> None:
        self.write(PRODUCT_LIQUID_MAP, data)

    def read_product_liquid_map(self) -> dict:
        return self.read(PRODUCT_LIQUID_MAP)

    def write_sanity_report(self, data: dict) -> None:
        self.write(SANITY_REPORT, data)

    def read_sanity_report(self) -> dict:
        return self.read(SANITY_REPORT)

    def write_section_map(self, data: dict) -> None:
        self.write(SECTION_MAP, data)

    def read_section_map(self) -> dict:
        return self.read(SECTION_MAP)

    def write_app_classification(self, data: list) -> None:
        self.write(APP_CLASSIFICATION, data)

    def read_app_classification(self) -> list:
        return self.read(APP_CLASSIFICATION)

    def write_sections_draft(self, data: dict) -> None:
        self.write(SECTIONS_DRAFT, data)

    def read_sections_draft(self) -> dict:
        return self.read(SECTIONS_DRAFT)

    def write_compliance_report(self, data: dict) -> None:
        self.write(COMPLIANCE_REPORT, data)

    def read_compliance_report(self) -> dict:
        return self.read(COMPLIANCE_REPORT)

    def write_regression_report(self, data: dict) -> None:
        self.write(REGRESSION_REPORT, data)

    def read_regression_report(self) -> dict:
        return self.read(REGRESSION_REPORT)

    def write_summary(self, data: dict) -> None:
        self.write(PIPELINE_SUMMARY, data)

    # ── factory ───────────────────────────────────────────────────────────────

    @classmethod
    def create_new(cls) -> "RunState":
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        return cls(run_id)

    @classmethod
    def load(cls, run_id: str) -> "RunState":
        state = cls(run_id)
        if not state.run_dir.exists():
            raise FileNotFoundError(f"Run not found: {run_id}")
        return state
