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

# Below this, treat the fetch as failed rather than draft off near-empty text
# (typically a bot-detection interstitial, not the real page).
MIN_TEXT_LEN = 200

# Flags automation fingerprinting checks for; without these, cloud CI IPs
# (GitHub-hosted runners) get served a reduced/challenge page by some sites
# (confirmed on openai.com: 2.3k chars extracted from a residential IP,
# 68 chars -- a bot-check interstitial -- from a GitHub Actions runner).
STEALTH_INIT_SCRIPT = "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"


def fetch_rendered_html(url: str, timeout_ms: int = 30000) -> str:
    with sync_playwright() as p:
        # channel="chromium" forces the full Chromium build rather than the
        # separate headless-shell variant, so only `playwright install
        # chromium` is needed (no extra headless-shell download).
        browser = p.chromium.launch(
            channel="chromium",
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = browser.new_page(user_agent=USER_AGENT, locale="en-US")
        page.add_init_script(STEALTH_INIT_SCRIPT)
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


def fetch_one(cid: str, url: str) -> str:
    """Fetch+extract, retrying once with a longer settle window if the page
    looks like it didn't render (bot-check interstitial, slow hydration)."""
    for attempt, extra_wait_ms in enumerate((2000, 6000)):
        html = fetch_rendered_html(url) if attempt == 0 else _fetch_with_wait(url, extra_wait_ms)
        text = extract_text(html, url)
        if len(text) >= MIN_TEXT_LEN:
            return text
        print(f"[fetch] {cid}: attempt {attempt + 1} got only {len(text)} chars", file=sys.stderr)
    return text  # caller decides whether this is usable


def _fetch_with_wait(url: str, wait_ms: int) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="chromium",
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = browser.new_page(user_agent=USER_AGENT, locale="en-US")
        page.add_init_script(STEALTH_INIT_SCRIPT)
        page.goto(url, timeout=30000, wait_until="load")
        page.wait_for_timeout(wait_ms)
        html = page.content()
        browser.close()
        return html


def fetch_all() -> dict:
    comparisons = json.loads(COMPARISONS_FILE.read_text())
    results = {}
    for comp in comparisons["competitors"]:
        cid, url = comp["id"], comp["track_url"]
        print(f"[fetch] {cid} <- {url}", file=sys.stderr)
        text = fetch_one(cid, url)
        if len(text) < MIN_TEXT_LEN:
            print(f"[fetch] SKIPPING {cid}: only {len(text)} chars after retry, likely bot-blocked -- not drafting off this", file=sys.stderr)
            continue
        results[cid] = {"url": url, "text": text}
    return results


if __name__ == "__main__":
    print(json.dumps(fetch_all(), indent=2))
