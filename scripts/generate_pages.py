#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parents[1]
DAILY_DIR = ROOT / "daily"
DOCS_DIR = ROOT / "docs"
DOCS_DAILY_DIR = DOCS_DIR / "daily"
DATE_FILE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.json$")

MARKDOWN = (
    MarkdownIt("commonmark", {"html": False, "linkify": False, "typographer": False})
    .enable("table")
    .enable("strikethrough")
)


def esc(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def load_reports() -> list[tuple[str, list[dict[str, Any]]]]:
    reports: list[tuple[str, list[dict[str, Any]]]] = []
    for path in DAILY_DIR.iterdir():
        match = DATE_FILE_RE.match(path.name)
        if not match:
            continue
        with path.open("r", encoding="utf-8") as handle:
            releases = json.load(handle)
        if not isinstance(releases, list):
            raise ValueError(f"{path} must contain a JSON array")
        for index, release in enumerate(releases):
            validate_release(path, index, release)
        reports.append((match.group(1), releases))
    reports.sort(key=lambda item: item[0])
    return reports


def validate_release(path: Path, index: int, release: Any) -> None:
    if not isinstance(release, dict):
        raise ValueError(f"{path}[{index}] must be a JSON object")

    required = ("repo", "tag", "url", "published_at", "prerelease", "body")
    missing = [field for field in required if field not in release]
    if missing:
        raise ValueError(f"{path}[{index}] missing fields: {', '.join(missing)}")
    if not isinstance(release["repo"], str) or not release["repo"]:
        raise ValueError(f"{path}[{index}].repo must be a non-empty string")
    if not isinstance(release["published_at"], str) or not release["published_at"]:
        raise ValueError(f"{path}[{index}].published_at must be a non-empty string")
    if not isinstance(release["prerelease"], bool):
        raise ValueError(f"{path}[{index}].prerelease must be a boolean")


def grouped_releases(releases: list[dict[str, Any]]) -> list[tuple[str, list[dict[str, Any]]]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for release in releases:
        groups[release["repo"]].append(release)

    for repo_releases in groups.values():
        repo_releases.sort(key=lambda release: release["published_at"], reverse=True)

    return sorted(
        groups.items(),
        key=lambda item: (item[1][0]["published_at"], item[0]),
        reverse=True,
    )


def render_release(release: dict[str, Any], expanded: bool) -> str:
    prerelease = release["prerelease"]
    status = "Prerelease" if prerelease else "Stable"
    status_class = "prerelease" if prerelease else "stable"
    tag = release.get("tag") or "(untagged release)"
    name = release.get("name")
    show_name = isinstance(name, str) and name.strip() and name.strip() != str(tag).strip()
    body = release.get("body")
    body_html = MARKDOWN.render(body) if isinstance(body, str) and body else "<p><em>No release notes provided.</em></p>"
    open_attr = " open" if expanded else ""

    title_html = f'<span class="release-tag">{esc(tag)}</span>'
    if show_name:
        title_html += f'<span class="release-name">{esc(name.strip())}</span>'

    return f'''<details class="release" data-prerelease="{str(prerelease).lower()}"{open_attr}>
  <summary>
    <span class="release-title">{title_html}</span>
    <span class="release-meta"><span class="badge {status_class}">{status}</span><time datetime="{esc(release['published_at'])}">{esc(release['published_at'])}</time></span>
  </summary>
  <div class="release-body markdown-body">
    {body_html}
    <p class="release-link"><a href="{esc(release['url'])}" rel="noopener noreferrer">View release →</a></p>
  </div>
</details>'''


def render_repo(repo: str, releases: list[dict[str, Any]]) -> str:
    stable = sum(not release["prerelease"] for release in releases)
    prerelease = len(releases) - stable
    count_parts = [f"{len(releases)} release{'s' if len(releases) != 1 else ''}"]
    if stable:
        count_parts.append(f"{stable} stable")
    if prerelease:
        count_parts.append(f"{prerelease} prerelease")
    release_html = "\n".join(
        render_release(release, expanded=(index == 0))
        for index, release in enumerate(releases)
    )
    return f'''<section class="repo-block" data-repo="{esc(repo)}">
  <header class="repo-header">
    <h2><a href="https://github.com/{esc(repo)}" rel="noopener noreferrer">{esc(repo)}</a></h2>
    <p>{" · ".join(count_parts)}</p>
  </header>
  <div class="release-list">
{release_html}
  </div>
</section>'''


def render_page(
    date: str,
    releases: list[dict[str, Any]],
    previous_date: str | None,
    next_date: str | None,
    *,
    root_page: bool,
) -> str:
    groups = grouped_releases(releases)
    repo_count = len(groups)
    release_count = len(releases)
    prefix = "" if root_page else "../"
    nav_prefix = "daily/" if root_page else ""

    previous_link = (
        f'<a class="nav-link" href="{nav_prefix}{previous_date}.html">← {previous_date}</a>'
        if previous_date
        else '<span class="nav-placeholder"></span>'
    )
    next_link = (
        f'<a class="nav-link" href="{nav_prefix}{next_date}.html">{next_date} →</a>'
        if next_date
        else '<span class="nav-placeholder"></span>'
    )

    if groups:
        repositories_html = "\n".join(render_repo(repo, repo_releases) for repo, repo_releases in groups)
    else:
        repositories_html = '<p class="empty-state">No releases were published in this report.</p>'

    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light dark">
  <title>GitHub Release Digest — {date}</title>
  <link rel="stylesheet" href="{prefix}assets/style.css">
</head>
<body>
  <main class="page-shell">
    <header class="page-header">
      <a class="site-title" href="{prefix}index.html">GitHub Release Digest</a>
      <h1>{date}</h1>
      <p class="totals">{repo_count} repositor{'y' if repo_count == 1 else 'ies'} · {release_count} release{'s' if release_count != 1 else ''}</p>
    </header>

    <nav class="date-nav" aria-label="Daily reports">
      {previous_link}
      {next_link}
    </nav>

    <div class="filters" role="group" aria-label="Release type filter">
      <button type="button" class="filter-button active" data-filter="all" aria-pressed="true">All</button>
      <button type="button" class="filter-button" data-filter="stable" aria-pressed="false">Stable</button>
      <button type="button" class="filter-button" data-filter="prerelease" aria-pressed="false">Prerelease</button>
    </div>

    <div id="repositories">
{repositories_html}
    </div>
  </main>
  <script src="{prefix}assets/app.js" defer></script>
</body>
</html>
'''


def generate() -> None:
    reports = load_reports()
    if not reports:
        raise RuntimeError("No daily/YYYY-MM-DD.json reports found")

    DOCS_DAILY_DIR.mkdir(parents=True, exist_ok=True)
    dates = [date for date, _ in reports]

    expected_pages = set()
    for index, (date, releases) in enumerate(reports):
        previous_date = dates[index - 1] if index > 0 else None
        next_date = dates[index + 1] if index + 1 < len(dates) else None
        output = DOCS_DAILY_DIR / f"{date}.html"
        output.write_text(
            render_page(date, releases, previous_date, next_date, root_page=False),
            encoding="utf-8",
        )
        expected_pages.add(output.name)

    for path in DOCS_DAILY_DIR.glob("*.html"):
        if path.name not in expected_pages:
            path.unlink()

    latest_date, latest_releases = reports[-1]
    previous_date = dates[-2] if len(dates) > 1 else None
    (DOCS_DIR / "index.html").write_text(
        render_page(latest_date, latest_releases, previous_date, None, root_page=True),
        encoding="utf-8",
    )

    print(f"Generated {len(reports)} daily pages; latest is {latest_date}.")


if __name__ == "__main__":
    generate()
