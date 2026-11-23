"""Collect public, read-only GitHub evidence, including every issue/PR page."""

import datetime as dt
import json
from pathlib import Path
import re
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


REPOSITORY = "wenyenhsu/llm-powered-daily-intelligence-system"
API = f"https://api.github.com/repos/{REPOSITORY}"


def main():
    requests = []

    def get(url):
        request = Request(url, headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "local-embedding-model-verification",
        })
        try:
            with urlopen(request, timeout=30) as response:
                data = json.load(response)
                requests.append({"url": url, "status": response.status, "data": data})
                return data, response.headers.get("Link", "")
        except HTTPError as error:
            requests.append({"url": url, "status": error.code, "body": error.read().decode()})
            if error.code == 404:
                return None, ""
            raise

    def pages(url):
        rows = []
        while url:
            data, links = get(url)
            if data is None:
                raise RuntimeError(f"Cannot enumerate {url}")
            rows.extend(data)
            next_link = re.search(r'<([^>]+)>; rel="next"', links)
            url = next_link.group(1) if next_link else None
        return rows

    issues_and_prs = pages(f"{API}/issues?state=all&per_page=100")
    pulls = pages(f"{API}/pulls?state=all&per_page=100")
    issues = [row for row in issues_and_prs if "pull_request" not in row]
    pattern = re.compile(r"embed|model|metadata|retriev|reindex|compatib", re.I)
    matches = [{"number": row["number"], "title": row["title"], "url": row["html_url"]}
               for row in issues + pulls if pattern.search(row["title"] + "\n" + (row["body"] or ""))]
    get(API)
    get(f"{API}/commits/main")
    for pull in pulls:
        get(f"{API}/pulls/{pull['number']}")
        pages(f"{API}/pulls/{pull['number']}/files?per_page=100")
    # GitHub can inherit default contribution guidelines from this repository.
    get("https://api.github.com/repos/wenyenhsu/.github/contents")
    summary = {
        "checked_at_los_angeles": dt.datetime.now(ZoneInfo("America/Los_Angeles")).isoformat(),
        "repository": REPOSITORY,
        "issue_counts": {state: sum(row["state"] == state for row in issues) for state in ("open", "closed")},
        "pull_counts": {state: sum(row["state"] == state for row in pulls) for state in ("open", "closed")},
        "title_body_search_pattern": pattern.pattern,
        "matching_items": matches,
    }
    Path("verification/github-search.json").write_text(
        json.dumps({"summary": summary, "requests": requests}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("All issue/PR pagination followed. Full API responses: verification/github-search.json")


if __name__ == "__main__":
    main()
