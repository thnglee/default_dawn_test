"""
Pipeline configuration — paths, model IDs, thresholds.
All paths are absolute. Nothing in here requires network access.
"""

import os
from pathlib import Path

# Auto-load .env from pipeline-registry/ (one level up from orchestrator/)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass  # python-dotenv not installed; rely on shell env

# ── Repository root ──────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).parent.parent.parent  # /…/dawntest

# ── Pipeline registry ────────────────────────────────────────────────────────
REGISTRY_DIR   = REPO_ROOT / "pipeline-registry"
SKILLS_DIR     = REGISTRY_DIR / "skills"
FINGERPRINTS   = REGISTRY_DIR / "fingerprints" / "app_signatures.json"
PROMPTS_DIR    = REGISTRY_DIR / "agent_prompts"
RUNS_DIR       = REGISTRY_DIR / "runs"

# ── Output locations (written directly into the repo) ────────────────────────
SECTIONS_OUT   = REPO_ROOT / "sections"
TEMPLATES_OUT  = REPO_ROOT / "templates"

# ── Claude models ────────────────────────────────────────────────────────────
MODEL_DEFAULT          = "claude-opus-4-6"   # layout, compliance, regression
MODEL_SECTION_CONVERT  = "claude-opus-4-6"   # highest-value prompt
MODEL_FAST             = "claude-opus-4-6"   # product sanity, app detection

# ── Playwright capture settings ───────────────────────────────────────────────
VIEWPORT_WIDTH   = 1280
VIEWPORT_HEIGHT  = 800   # height of each screenshot slice
PAGE_LOAD_WAIT   = 3000  # ms after navigation
MAX_VIEWPORTS    = 12    # safety cap

# ── LLM call settings ────────────────────────────────────────────────────────
MAX_TOKENS_DEFAULT         = 4096
MAX_TOKENS_SECTION_CONVERT = 6000
MAX_TOKENS_COMPLIANCE      = 5000

# ── Pipeline thresholds ──────────────────────────────────────────────────────
COMPLIANCE_MIN_SCORE          = 0.70   # below this → second pass
COMPLIANCE_MAX_PASSES         = 2
REGRESSION_MIN_SIMILARITY     = 0.75   # below this → re_convert
REGRESSION_MAX_RECONVERTS     = 1      # per section

# ── HTML snippet cap (chars) sent to section conversion ──────────────────────
MAX_HTML_SNIPPET_CHARS = 4000

# ── Section conversion parallelism ───────────────────────────────────────────
CONVERSION_MAX_WORKERS = 4

# ── High-priority sections checked by visual regression ──────────────────────
REGRESSION_PRIORITY_TYPES = {"product_gallery", "product_info"}

# ── Dawn version (pin to theme) ──────────────────────────────────────────────
DAWN_VERSION = "dawn-15.0"

# ── Env vars (never hardcode) ────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
FIGMA_API_TOKEN   = os.environ.get("FIGMA_API_TOKEN", "")   # optional
SHOPIFY_STORE     = os.environ.get("SHOPIFY_STORE", "")      # optional

# ── Validation ───────────────────────────────────────────────────────────────
def validate():
    """Call at startup. Raises if required env vars are missing."""
    if not ANTHROPIC_API_KEY:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY is not set. "
            "Run: export ANTHROPIC_API_KEY=your-key"
        )
