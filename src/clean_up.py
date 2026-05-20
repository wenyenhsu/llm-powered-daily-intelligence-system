from __future__ import annotations


from config import *



def normalize_target(raw: str) -> str:
    """
    [[topic/name|alias]] -> topic/name
    [[name]] -> name
    """
    raw = raw.strip()

    # 先去掉 alias
    if "|" in raw:
        raw = raw.split("|", 1)[0].strip()

    # 去掉前綴資料夾
    if "/" in raw:
        raw = raw.split("/", 1)[1].strip()

    return raw.lower()


def is_bad_target(raw: str) -> bool:
    return normalize_target(raw) in BAD_NODES


def clean_text(text: str) -> str:
    # 移除壞 wiki links
    def replace_link(match: re.Match[str]) -> str:
        target = match.group(1)
        if is_bad_target(target):
            return ""
        return match.group(0)

    text = WIKI_LINK_RE.sub(replace_link, text)

    # 移除空 bullet
    text = EMPTY_BULLET_RE.sub("", text)

    # 壓縮多餘空白行
    text = MULTI_BLANK_RE.sub("\n\n", text)

    return text


def should_skip(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.parts)


def delete_bad_node_files() -> None:
    """
    刪掉檔名本身就是壞 node 的 markdown 檔。
    例如 insights/summarized.md
    """
    for md in BASE_DIR.rglob("*.md"):
        if should_skip(md):
            continue

        if md.stem.lower() in BAD_NODES:
            print(f"Deleting bad node file: {md}")
            md.unlink()


def clean_all_markdown() -> None:
    for md in BASE_DIR.rglob("*.md"):
        if should_skip(md):
            continue

        original = md.read_text(encoding="utf-8")
        cleaned = clean_text(original)

        if cleaned != original:
            md.write_text(cleaned, encoding="utf-8")
            print(f"Cleaned: {md}")

