#!/usr/bin/env python3
"""Orchestrates the growth-ops agent: fetch -> diff -> draft -> PR.

Exit code is always 0 on a successful run (including "nothing changed") so
the GitHub Actions job doesn't go red just because no PR was needed.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fetch_snapshot import fetch_all  # noqa: E402
from diff_snapshot import diff_one, save_snapshot  # noqa: E402
from draft_update import draft_for  # noqa: E402
from open_pr import open_pr_for_updates  # noqa: E402

ROOT = Path(__file__).parent.parent
COMPARISONS_FILE = ROOT / "data" / "comparisons.json"


def main() -> None:
    comparisons = json.loads(COMPARISONS_FILE.read_text(encoding="utf-8"))
    by_id = {c["id"]: c for c in comparisons["competitors"]}

    fetched = fetch_all()
    updates = []
    for cid, result in fetched.items():
        diff_result = diff_one(cid, result["text"])
        if not diff_result["changed"]:
            print(f"[{cid}] no meaningful change (similarity={diff_result['similarity']:.3f}), skipping")
            continue

        label = "new page, capturing baseline" if diff_result["is_new"] else "change detected"
        print(f"[{cid}] {label}, drafting update")
        try:
            draft = draft_for(by_id[cid], diff_result)
        except Exception as e:
            # One competitor's draft failing (rate limit, bad JSON from the
            # model, etc.) shouldn't sink a run that found real changes
            # elsewhere -- skip it, keep going, still open a PR for the rest.
            print(f"[{cid}] drafting failed, skipping this competitor: {e}")
            continue
        updates.append({
            "cid": cid,
            "draft": draft,
            "diff": diff_result["diff"] or diff_result["new_text"],
        })
        save_snapshot(cid, result["text"])

    if not updates:
        print("Nothing changed across tracked competitors. No PR opened.")
        return

    pr_url = open_pr_for_updates(updates)
    print(f"Opened PR: {pr_url}")


if __name__ == "__main__":
    main()
