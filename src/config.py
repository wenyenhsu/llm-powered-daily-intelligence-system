from pathlib import Path
from datetime import datetime
import os
import re

# =========================================================
# Paths
# =========================================================

BASE_DIR = Path(__file__).resolve().parents[1]

INBOX_DIR = BASE_DIR / "inbox"
DAILY_DIR = BASE_DIR / "daily"
PROMPTS_DIR = BASE_DIR / "prompts"
SRC_DIR = BASE_DIR / "src"
CONFIGS_DIR = BASE_DIR / "configs"
INSIGHTS_DIR = BASE_DIR / "insights"
TOPICS_DIR = BASE_DIR / "topics"

STATE_DIR = BASE_DIR / "state"
ENV_FILE = BASE_DIR / ".env"

# =========================================================
# State files
# =========================================================

INSIGHT_INDEX_FILE = STATE_DIR / "insight_index.json"
TOPIC_INDEX_FILE = STATE_DIR / "topic_index.json"

# =========================================================
# Runtime & LLM Config
# =========================================================

TODAY = datetime.now().strftime("%Y-%m-%d")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

# =========================================================
# Cleanup rules
# =========================================================

SKIP_DIRS = {
    ".obsidian",
    ".git",
    "node_modules",
    "__pycache__",
    "prompts",
}

BAD_NODES = {
    "summarized",
    "url",
    "...",
    "this-news-about-ai",
    "openai-new-model-may-2026",
}

# =========================================================
# Link patterns
# =========================================================

WIKI_LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
INSIGHT_LINK_RE = re.compile(r"\[\[insights/([^\]|]+)(?:\|[^\]]+)?\]\]")
TOPIC_LINK_RE = re.compile(r"\[\[topics/([^\]|]+)(?:\|[^\]]+)?\]\]")

# =========================================================
# Text cleanup
# =========================================================

EMPTY_BULLET_RE = re.compile(r"^\s*[-*]\s*$", re.MULTILINE)
MULTI_BLANK_RE = re.compile(r"\n{3,}")
HEADING_RE = re.compile(r"^# .*$", re.MULTILINE)
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
DERIVED_FROM_RE = re.compile(r"Derived from\s+daily/(\d{4}-\d{2}-\d{2})", re.IGNORECASE)
ANSI_ESCAPE_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
INVISIBLE_RE = re.compile(r"[\u200b\u200c\u200d\u2060\ufeff\u00ad]")
BULLET_RE = re.compile(r"^(\s*[-*+]\s+)(.*)$")

# =========================================================
# Extraction block
# =========================================================

EXTRACTION_BLOCK_RE = re.compile(
    r"## Extraction Block(.*?)<!-- END EXTRACTION -->",
    flags=re.S,
)

# =========================================================
# Required report sections
# =========================================================

REQUIRED_SECTIONS = [
    "## Executive Summary",
    "## Major Themes",
    "## Key Signals",
    "## Risks and Watchlist",
    "## Supporting Insights",
]