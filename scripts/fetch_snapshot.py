#!/usr/bin/env python3
"""Fetch each tracked competitor page and extract clean text.

Uses a real headless browser (Playwright) rather than plain HTTP requests:
some tracked pages (e.g. openai.com) sit behind bot-detection that returns a
403 to a bare `requests.get`, even with a browser-like User-Agent, but
renders normally for an actual browser.
"""
import json
import sys
from pathlib import Path

import trafilatura
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).parent.parent
COMPARISONS_FILE = ROOT / "data" / "comparisons.json"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)


def fetch_rendered_html(url: str, timeout_ms: int = 30000) -> str:
    with sync_playwright() as p:
        # channel="chromium" forces the full Chromium build rather than the
        # separate headless-shell variant, so only `playwright install
        # chromium` is needed (no extra headless-shell download).
        browser = p.chromium.launch(channel="chromium")
        page = browser.new_page(user_agent=USER_AGENT)
        # "networkidle" hangs on pages with persistent background activity
        # (analytics, websockets) -- wait for "load" plus a short settle
        # window for post-load hydration instead.
        page.goto(url, timeout=timeout_ms, wait_until="load")
        page.wait_for_timeout(2000)
        html = page.content()
        browser.close()
        return html


def extract_text(html: str, url: str) -> str:
    return trafilatura.extract(html, url=url, include_links=False, include_tables=True) or ""


def fetch_all() -> dict:
    comparisons = json.loads(COMPARISONS_FILE.read_text())
    results = {}
    for comp in comparisons["competitors"]:
        cid, url = comp["id"], comp["track_url"]
        print(f"[fetch] {cid} <- {url}", file=sys.stderr)
        html = fetch_rendered_html(url)
        text = extract_text(html, url)
        if len(text) < 200:
            print(f"[fetch] WARNING: {cid} extracted only {len(text)} chars, page may not have rendered", file=sys.stderr)
        results[cid] = {"url": url, "text": text}
    return results


if __name__ == "__main__":
    print(json.dumps(fetch_all(), indent=2))
