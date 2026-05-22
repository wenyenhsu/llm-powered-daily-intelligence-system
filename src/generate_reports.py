"""Report generation utilities for daily, weekly, and monthly synthesis.

This module is designed to be imported from `run_pipeline.py`.

Example:
    from src.generate_reports import generate_reports

    result = generate_reports(
        granularity="day",
        target_date="2026-05-18",
        source_dir="insights",
        output_dir="reports",
        prompt_dir="prompts",
        provider="openai",
    )
    print(result.output_path)

CLI example:
    python src/generate_reports.py --granularity day --date 2026-05-18
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass
from logging import exception
from typing import Any, Callable, Optional
from src.config import *

@dataclass(slots=True)
class InsightItem:
    title: str
    body: str
    source_path: Path
    date: dt.date
    topic: str | None = None
    tags: list[str] | None = None
    raw: dict[str, Any] | None = None

    @property
    def text(self) -> str:
        parts = [self.title.strip(), self.body.strip()]
        return "\n".join(p for p in parts if p)


@dataclass(slots=True)
class ReportWindow:
    granularity: str
    target_date: dt.date
    start: dt.date
    end: dt.date

    @property
    def label(self) -> str:
        if self.granularity == "day":
            return self.start.isoformat()

        if self.granularity == "week":
            year, week, _ = self.start.isocalendar()
            return f"{year}-W{week:02d}"

        if self.granularity == "month":
            return f"{self.start.year:04d}-{self.start.month:02d}"

        if self.start == self.end:
            return self.start.isoformat()

        return f"{self.start.isoformat()}_to_{self.end.isoformat()}"


@dataclass(slots=True)
class ReportResult:
    granularity: str
    target_date: dt.date
    window: ReportWindow
    output_path: Path
    content: str
    item_count: int

LLMCallable = Callable[[str, str, str], str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate daily, weekly, or monthly reports from insights.")
    parser.add_argument("--granularity", choices=("day", "week", "month"), required=True)
    parser.add_argument("--date", required=True, help="Target date in YYYY-MM-DD format.")
    parser.add_argument("--source-dir", default="insights", help="Directory containing insight files.")
    parser.add_argument("--output-dir", default="reports", help="Directory for generated reports.")
    parser.add_argument("--prompt-dir", default="prompts", help="Directory containing prompt templates.")
    parser.add_argument("--model", default=os.getenv("REPORT_MODEL", "gpt-4.1-mini"), help="Model name to use.")
    parser.add_argument(
        "--provider",
        choices=("openai", "template"),
        default=os.getenv("REPORT_PROVIDER", "openai"),
        help="LLM provider. Falls back to template when unavailable.",
    )
    parser.add_argument("--max-items", type=int, default=80, help="Maximum insight items to include in context.")
    parser.add_argument("--max-chars-per-item", type=int, default=1800, help="Maximum chars kept per insight body.")
    parser.add_argument("--dry-run", action="store_true", help="Print the report content without writing a file.")
    parser.add_argument("--include-mtime", action="store_true", help="Use file modification time if no date metadata exists.")
    return parser.parse_args()


def parse_date(date_str: str) -> dt.date:
    try:
        return dt.date.fromisoformat(date_str)
    except ValueError as exc:
        raise SystemExit(f"Invalid --date value: {date_str!r}. Expected YYYY-MM-DD.") from exc


def get_report_window(granularity: str, target_date: dt.date) -> ReportWindow:
    if granularity == "day":
        start = end = target_date
    elif granularity == "week":
        start = target_date - dt.timedelta(days=target_date.weekday())
        end = start + dt.timedelta(days=6)
    elif granularity == "month":
        start = target_date.replace(day=1)
        if start.month == 12:
            next_month = dt.date(start.year + 1, 1, 1)
        else:
            next_month = dt.date(start.year, start.month + 1, 1)
        end = next_month - dt.timedelta(days=1)
    else:
        raise ValueError(f"Unsupported granularity: {granularity}")
    return ReportWindow(granularity=granularity, target_date=target_date, start=start, end=end)


def ensure_dirs(*paths: Path) -> None:
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text

    raw = match.group(1)
    body = text[match.end():]
    meta: dict[str, Any] = {}
    current_key: str | None = None

    for line in raw.splitlines():
        if not line.strip():
            continue
        if line.startswith("  - ") and current_key:
            meta.setdefault(current_key, []).append(line[4:].strip())
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip().lower()
            value = value.strip()
            current_key = key
            if not value:
                meta[key] = []
            elif value.startswith("[") and value.endswith("]"):
                inner = value[1:-1].strip()
                meta[key] = [part.strip().strip('"\'') for part in inner.split(",") if part.strip()]
            else:
                meta[key] = value.strip('"\'')
        elif current_key and isinstance(meta.get(current_key), list):
            meta[current_key].append(line.strip().lstrip("- ").strip())

    return meta, body


def parse_date_from_any(value: Any) -> Optional[dt.date]:
    if value is None:
        return None
    if isinstance(value, dt.date) and not isinstance(value, dt.datetime):
        return value
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        try:
            return dt.date.fromisoformat(value[:10])
        except ValueError:
            m = DATE_RE.search(value)
            if m:
                try:
                    return dt.date.fromisoformat(m.group(1))
                except ValueError:
                    return None
    return None


def infer_date_from_path(path: Path) -> Optional[dt.date]:
    m = DATE_RE.search(path.stem) or DATE_RE.search(str(path))
    if not m:
        return None
    try:
        return dt.date.fromisoformat(m.group(1))
    except ValueError:
        return None

def infer_date_from_text(text: str) -> Optional[dt.date]:
    m = DERIVED_FROM_RE.search(text)
    if m:
        try:
            return dt.date.fromisoformat(m.group(1))
        except ValueError:
            return None

    m = DATE_RE.search(text)
    if m:
        try:
            return dt.date.fromisoformat(m.group(1))
        except ValueError:
            return None
    return None

def file_mtime_date(path: Path) -> dt.date:
    return dt.datetime.fromtimestamp(path.stat().st_mtime).date()


def normalize_tags(value: Any) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        return [v.strip() for v in re.split(r"[,;]", value) if v.strip()]
    return [str(value).strip()]


def load_insight_from_json(obj: dict[str, Any], path: Path, default_date: Optional[dt.date]) -> Optional[InsightItem]:
    if not isinstance(obj, dict):
        return None
    title = str(obj.get("title") or obj.get("name") or path.stem).strip()
    body = str(obj.get("body") or obj.get("content") or obj.get("text") or "").strip()
    date = parse_date_from_any(obj.get("date") or obj.get("created_at") or obj.get("published_at") or obj.get("updated_at"))
    if date is None:
        date = default_date
    if date is None:
        return None
    topic = obj.get("topic") or obj.get("cluster") or obj.get("category")
    topic = str(topic).strip() if topic is not None else None
    tags = normalize_tags(obj.get("tags"))
    return InsightItem(title=title, body=body, source_path=path, date=date, topic=topic, tags=tags, raw=obj)


def load_insights(source_dir: Path, include_mtime: bool = False) -> list[InsightItem]:
    if not source_dir.exists():
        raise SystemExit(f"Source directory does not exist: {source_dir}")

    items: list[InsightItem] = []
    for path in sorted(source_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".md", ".markdown", ".txt", ".json", ".jsonl"}:
            continue

        default_date = infer_date_from_path(path)
        if include_mtime and default_date is None:
            default_date = file_mtime_date(path)

        try:
            if path.suffix.lower() in {".json", ".jsonl"}:
                with path.open("r", encoding="utf-8") as f:
                    if path.suffix.lower() == ".jsonl":
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            obj = json.loads(line)
                            item = load_insight_from_json(obj, path, default_date)
                            if item:
                                items.append(item)
                    else:
                        obj = json.load(f)
                        if isinstance(obj, list):
                            for entry in obj:
                                item = load_insight_from_json(entry, path, default_date)
                                if item:
                                    items.append(item)
                        else:
                            item = load_insight_from_json(obj, path, default_date)
                            if item:
                                items.append(item)
                continue

            text = path.read_text(encoding="utf-8")
            meta, body = parse_frontmatter(text)

            date = (
                parse_date_from_any(meta.get("date"))
                or parse_date_from_any(meta.get("created_at"))
                or parse_date_from_any(meta.get("published_at"))
                or parse_date_from_any(meta.get("updated_at"))
                or infer_date_from_path(path)
                or infer_date_from_text(text)
                or (file_mtime_date(path) if include_mtime else None)
            )

            if date is None:
                continue

            title = str(meta.get("title") or meta.get("name") or path.stem).strip()
            topic = meta.get("topic") or meta.get("cluster") or meta.get("category")
            topic = str(topic).strip() if topic is not None else None
            tags = normalize_tags(meta.get("tags"))
            body = body.strip()

            items.append(
                InsightItem(
                    title=title,
                    body=body,
                    source_path=path,
                    date=date,
                    topic=topic,
                    tags=tags,
                    raw=meta,
                )
            )
        except Exception as exc:
            print(f"[warn] Skipping {path}: {exc}", file=sys.stderr)

    return items


def filter_items(
    items: list[InsightItem],
    window: ReportWindow,
    max_items: int,
    max_chars_per_item: int,
) -> list[InsightItem]:

    selected = [
        item
        for item in items
        if window.start <= item.date <= window.end
    ]

    selected.sort(
        key=lambda x: (
            x.date,
            x.topic or "",
            x.title,
        )
    )

    trimmed: list[InsightItem] = []

    for item in selected[:max_items]:
        body = item.body

        if len(body) > max_chars_per_item:
            body = body[:max_chars_per_item].rstrip() + "..."

        trimmed.append(
            InsightItem(
                title=item.title,
                body=body,
                source_path=item.source_path,
                date=item.date,
                topic=item.topic,
                tags=item.tags,
                raw=item.raw,
            )
        )

    return trimmed


def compute_topic_counts(items: list[InsightItem]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for item in items:
        if item.topic:
            counter[item.topic] += 1
        for tag in item.tags or []:
            counter[tag] += 1
    return counter


STOPWORDS = {
    "the", "and", "for", "that", "with", "from", "this", "have", "are", "was", "were", "will", "into",
    "their", "about", "they", "them", "your", "you", "our", "not", "can", "has", "had", "but", "been",
    "also", "more", "than", "less", "via", "when", "what", "which", "who", "how", "why", "all", "any",
    "its", "new", "use", "used", "should", "could", "would", "may", "might", "today", "week", "month",
}


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in re.findall(r"[A-Za-z][A-Za-z0-9\-]+", text)]


def top_terms(items: list[InsightItem], top_n: int = 12) -> list[tuple[str, int]]:
    counter: Counter[str] = Counter()
    for item in items:
        for token in tokenize(item.text):
            if token in STOPWORDS or len(token) <= 2:
                continue
            counter[token] += 1
    return counter.most_common(top_n)


def summarize_items_locally(items: list[InsightItem], window: ReportWindow) -> str:
    topic_counts = compute_topic_counts(items)
    terms = top_terms(items, top_n=10)
    lines = []
    lines.append(f"# {window.granularity.capitalize()} Report ({window.label})")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append(f"Collected {len(items)} insight item(s) from {window.start.isoformat()} to {window.end.isoformat()}.")
    if topic_counts:
        top_topics = ", ".join(f"{name} ({count})" for name, count in topic_counts.most_common(5))
        lines.append(f"Most frequent topics/tags: {top_topics}.")
    if terms:
        top_terms_str = ", ".join(f"{term} ({count})" for term, count in terms[:5])
        lines.append(f"Repeated terms: {top_terms_str}.")
    lines.append("")
    lines.append("## Major Themes")
    if topic_counts:
        for name, count in topic_counts.most_common(8):
            lines.append(f"- {name}: {count} item(s)")
    else:
        lines.append("- No explicit topics were found.")
    lines.append("")
    lines.append("## Key Signals")
    for item in items[:10]:
        lines.append(f"- {item.date.isoformat()} — {item.title}")
    lines.append("")
    lines.append("## Risks and Watchlist")
    lines.append("- Review the generated report context and add model-driven synthesis if needed.")
    lines.append("")
    lines.append("## Supporting Insights")
    for item in items[:10]:
        snippet = item.body.replace("\n", " ").strip()
        if len(snippet) > 240:
            snippet = snippet[:237].rstrip() + "..."
        lines.append(f"- **{item.title}** ({item.date.isoformat()}): {snippet}")
    return "\n".join(lines).strip() + "\n"


def build_context(items: list[InsightItem], window: ReportWindow) -> str:
    topic_counts = compute_topic_counts(items)
    term_counts = top_terms(items, top_n=15)

    header = [
        f"Granularity: {window.granularity}",
        f"Target date: {window.target_date.isoformat()}",
        f"Window start: {window.start.isoformat()}",
        f"Window end: {window.end.isoformat()}",
        f"Item count: {len(items)}",
        "",
        "Top topics/tags:",
    ]
    if topic_counts:
        header.extend([f"- {name}: {count}" for name, count in topic_counts.most_common(12)])
    else:
        header.append("- (none found)")

    header.append("")
    header.append("Repeated terms:")
    if term_counts:
        header.extend([f"- {term}: {count}" for term, count in term_counts])
    else:
        header.append("- (none found)")

    header.append("")
    header.append("Insights:")

    for idx, item in enumerate(items, start=1):
        tags = ", ".join(item.tags or []) if item.tags else ""
        topic = item.topic or ""
        snippet = item.body.replace("\n", " ").strip()
        snippet = re.sub(r"\s+", " ", snippet)
        if len(snippet) > 1800:
            snippet = snippet[:1800].rstrip() + "..."
        header.append(f"[{idx}] date={item.date.isoformat()} topic={topic} tags={tags}")
        header.append(f"title: {item.title}")
        header.append(f"source: {item.source_path.as_posix()}")
        header.append(f"content: {snippet}")
        header.append("")

    return "\n".join(header).strip() + "\n"

# for date
def build_custom_window(
    granularity: str,
    start_date: str | dt.date,
    end_date: str | dt.date,
) -> ReportWindow:
    if isinstance(start_date, str):
        start_date = parse_date(start_date)

    if isinstance(end_date, str):
        end_date = parse_date(end_date)

    return ReportWindow(
        granularity=granularity,
        target_date=end_date,
        start=start_date,
        end=end_date,
    )

def load_prompt(prompt_dir: Path, granularity: str) -> str:
    mapping = {
        "day": "daily_report.md",
        "week": "weekly_report.md",
        "month": "monthly_report.md",
    }

    filename = mapping[granularity]
    path = prompt_dir / filename

    if not path.exists():
        raise FileNotFoundError(
            f"Missing prompt file: {path.as_posix()}"
        )

    return path.read_text(encoding="utf-8").strip()


def format_user_prompt(template: str, window: ReportWindow, items: list[InsightItem], context: str) -> str:
    return (
        f"{template}\n\n"
        f"Report granularity: {window.granularity}\n"
        f"Target date: {window.target_date.isoformat()}\n"
        f"Window: {window.start.isoformat()} to {window.end.isoformat()}\n"
        f"Insight count: {len(items)}\n\n"
        f"Use the following context:\n\n{context}"
    )


def call_openai(prompt: str, model: str) -> str:
    try:
        from openai import OpenAI  # type: ignore
    except Exception as exc:
        raise RuntimeError("OpenAI SDK is not installed. Install `openai` or use provider='template'.") from exc

    client = OpenAI()
    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": "You produce clean markdown reports from structured research notes."},
            {"role": "user", "content": prompt},
        ],
    )

    text = getattr(response, "output_text", None)
    if text:
        return text.strip() + "\n"

    chunks: list[str] = []
    for output_item in getattr(response, "output", []) or []:
        for content_item in getattr(output_item, "content", []) or []:
            if getattr(content_item, "type", None) in {"output_text", "text"}:
                chunks.append(getattr(content_item, "text", ""))
    if chunks:
        return "".join(chunks).strip() + "\n"

    raise RuntimeError("OpenAI response did not contain any text output.")


def call_llm(prompt: str, provider: str, model: str, llm_callable: LLMCallable | None = None) -> str:
    if llm_callable is not None:
        return llm_callable(prompt, provider, model)
    if provider == "template":
        return ""
    try:
        return call_openai(prompt, model)
    except Exception as exc:
        print(f"[warn] LLM generation failed, using local template fallback: {exc}", file=sys.stderr)
        return ""


# -------------------
# output the report
# -------------------
def strip_ansi(text: str) -> str:
    return ANSI_ESCAPE_RE.sub("", text)


def clean_report(text: str) -> str:
    if not text:
        return ""

    text = ANSI_ESCAPE_RE.sub("", text)
    text = text.replace("\r\n", "\n")
    text = unicodedata.normalize("NFKC", text)

    # remove invisible / soft hyphen characters
    text = INVISIBLE_RE.sub("", text)

    # remove <think> blocks
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S | re.I)

    # remove leading Thinking... blocks
    text = re.sub(r"(?is)^Thinking\.\.\..*?(?=\n\n|\Z)", "", text)

    # remove vector / chunk tags
    text = re.sub(r"\[\d+D\]\s*\[K\]", "", text)
    text = re.sub(r"\[\d+D\]", "", text)
    text = re.sub(r"\[K\]", "", text)

    # normalize spaces inside lines, but keep paragraph breaks
    lines = []
    for line in text.splitlines():
        line = re.sub(r"[ \t]+", " ", line).rstrip()
        lines.append(line)

    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip() + "\n"


def has_required_structure(text: str) -> bool:
    return sum(section in text for section in REQUIRED_SECTIONS) >= 3


def repair_report_text(
    bad_output: str,
    provider: str,
    model: str,
    llm_callable: LLMCallable | None = None,
) -> str:
    repair_prompt = f"""
You are a report formatter.

Rewrite the text below into the exact required report format.

Rules:
- Output ONLY the final report
- Do NOT include thinking, reasoning, notes, or citations
- Use exactly these sections:
  - ## Executive Summary
  - ## Major Themes
  - ## Key Signals
  - ## Risks and Watchlist
  - ## Supporting Insights

Source text:
{bad_output}
""".strip()

    repaired = call_llm(repair_prompt, provider, model, llm_callable=llm_callable)
    return clean_report(repaired)


def render_report(
    items: list[InsightItem],
    window: ReportWindow,
    provider: str,
    model: str,
    prompt_dir: Path,
    llm_callable: LLMCallable | None = None,
) -> str:
    template = load_prompt(prompt_dir, window.granularity)
    context = build_context(items, window)
    prompt = format_user_prompt(template, window, items, context)

    llm_output = call_llm(prompt, provider, model, llm_callable=llm_callable)
    llm_output = clean_report(llm_output)

    if has_required_structure(llm_output):
        return llm_output

    repaired = repair_report_text(
        bad_output=llm_output,
        provider=provider,
        model=model,
        llm_callable=llm_callable,
    )

    if has_required_structure(repaired):
        return repaired

    return clean_report(summarize_items_locally(items, window))


def output_path(output_dir: Path, window: ReportWindow) -> Path:
    if window.granularity == "day":
        return output_dir / "daily" / f"{window.label}.md"
    if window.granularity == "week":
        return output_dir / "weekly" / f"{window.label}.md"
    if window.granularity == "month":
        return output_dir / "monthly" / f"{window.label}.md"
    if window.granularity == "all":
        return output_dir / "all" / f"{window.label}.md"
    raise ValueError(f"Unsupported granularity: {window.granularity}")


def write_report(path: Path, content: str) -> None:
    ensure_dirs(path.parent)
    path.write_text(clean_report(content), encoding="utf-8")



def generate_reports(
    granularity: str,
    target_date: str | dt.date | None = None,
    source_dir: str | Path = "insights",
    output_dir: str | Path = "reports",
    prompt_dir: str | Path = "prompts",
    provider: str = "template",
    model: str = "gpt-4.1-mini",
    max_items: int = 80,
    max_chars_per_item: int = 1800,
    include_mtime: bool = False,
    dry_run: bool = False,
    llm_callable: LLMCallable | None = None,
    start_date: str | dt.date | None = None,
    end_date: str | dt.date | None = None,
) -> ReportResult:
    """Generate one report and return the result object."""
    target_dt = None

    if isinstance(target_date, str):
        target_dt = parse_date(target_date)

    elif isinstance(target_date, dt.date):
        target_dt = target_date

    if target_date is None and not (start_date and end_date):
        raise ValueError(
            "Either target_date or start_date/end_date is required."
        )

    target_dt = None
    if isinstance(target_date, str):
        target_dt = parse_date(target_date)
    elif isinstance(target_date, dt.date):
        target_dt = target_date

    if start_date is not None and end_date is not None:
        window = build_custom_window(
            granularity,
            start_date,
            end_date,
        )
    else:
        if target_dt is None:
            raise ValueError(
                "target_date is required when no custom range is provided."
            )

        window = get_report_window(
            granularity,
            target_dt,
        )
    source_path = Path(source_dir)
    output_path_root = Path(output_dir)
    prompt_path = Path(prompt_dir)

    ensure_dirs(output_path_root)

    all_items = load_insights(source_path, include_mtime=include_mtime)
    selected = filter_items(
        all_items,
        window,
        max_items=max_items,
        max_chars_per_item=max_chars_per_item,
    )

    if not selected:
        raise ValueError(
            f"No insights found for {window.granularity} window "
            f"{window.start.isoformat()} to {window.end.isoformat()}"
        )

    effective_provider = provider if llm_callable is not None else "template"
    report = render_report(
        selected,
        window,
        effective_provider,
        model,
        prompt_path,
        llm_callable=llm_callable,
    )
    report = clean_report(report)
    out_path = output_path(output_path_root, window)

    if not dry_run:
        write_report(out_path, report)

    if start_date is not None and end_date is not None:
        start_label = start_date.isoformat() if isinstance(start_date, dt.date) else str(start_date)
        end_label = end_date.isoformat() if isinstance(end_date, dt.date) else str(end_date)
        print(f"Generating reports from {start_label} to {end_label}")
    else:
        print(f"Generating reports for {target_dt.isoformat()}")

    return ReportResult(
        granularity=granularity,
        target_date=target_dt,
        window=window,
        output_path=out_path,
        content=report,
        item_count=len(selected),
    )

#-------------------
# output the report-end
#-------------------


def main() -> int:
    args = parse_args()
    try:
        result = generate_reports(
            granularity=args.granularity,
            target_date=args.date,
            source_dir=args.source_dir,
            output_dir=args.output_dir,
            prompt_dir=args.prompt_dir,
            provider=args.provider,
            model=args.model,
            max_items=args.max_items,
            include_mtime=args.include_mtime,
            dry_run=args.dry_run,
        )
    except Exception as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 2

    if args.dry_run:
        print(result.content)
    else:
        print(f"Wrote {result.output_path.as_posix()} ({result.item_count} insight item(s)).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())