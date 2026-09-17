#!/usr/bin/env python3
"""Commit the agent's drafted updates to data/comparisons.json and open a real PR.

Uses the `gh` CLI (already authenticated via GITHUB_TOKEN in Actions) rather
than a bespoke API client -- one less thing to get wrong, and it's what a
human maintaining this by hand would reach for too.
"""
import json
import subprocess
from datetime import date, timezone, datetime
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.parent
COMPARISONS_FILE = ROOT / "data" / "comparisons.json"


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(args, check=True, text=True, capture_output=True, cwd=ROOT)


def open_pr_for_updates(updates: list[dict]) -> Optional[str]:
    if not updates:
        return None

    today = date.today().isoformat()
    branch = f"growth-ops/{today}-{'-'.join(u['cid'] for u in updates)}"
    _run("git", "checkout", "-b", branch)

    comparisons = json.loads(COMPARISONS_FILE.read_text(encoding="utf-8"))
    by_id = {c["id"]: c for c in comparisons["competitors"]}

    body_sections = []
    for u in updates:
        entry = by_id[u["cid"]]
        entry["stronger_for"] = u["draft"]["stronger_for"]
        entry["lightsprint_better_for"] = u["draft"]["lightsprint_better_for"]
        entry["last_reviewed"] = today
        entry["source"] = f"growth-ops-agent, auto-drafted {today}"
        diff_excerpt = u["diff"][:2000]
        body_sections.append(
            f"### {entry['name']}\n{u['draft']['changelog_note']}\n\n"
            f"<details><summary>What the crawler saw change</summary>\n\n"
            f"```diff\n{diff_excerpt}\n```\n</details>"
        )

    comparisons["last_updated"] = today
    COMPARISONS_FILE.write_text(json.dumps(comparisons, indent=2) + "\n", encoding="utf-8")

    _run("git", "add", "data/comparisons.json", "data/snapshots")
    _run(
        "git", "-c", "user.name=growth-ops-agent",
        "-c", "user.email=growth-ops-agent@users.noreply.github.com",
        "commit", "-m",
        f"growth-ops-agent: refresh comparison copy ({', '.join(u['cid'] for u in updates)})",
    )
    _run("git", "push", "-u", "origin", branch)

    title = f"Growth-ops agent: refresh comparison copy ({', '.join(u['cid'] for u in updates)})"
    body = (
        "Opened automatically by the growth-ops agent after detecting a change on a "
        "tracked competitor page. **Nothing here ships without human approval** -- "
        "review the diff below, edit the copy inline if needed, then merge.\n\n"
        + "\n\n".join(body_sections)
        + f"\n\n---\nRun at {datetime.now(timezone.utc).isoformat(timespec='seconds')}Z"
    )
    result = _run("gh", "pr", "create", "--title", title, "--body", body, "--base", "main", "--head", branch)
    return result.stdout.strip()
