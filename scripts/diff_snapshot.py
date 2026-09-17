#!/usr/bin/env python3
"""Compare freshly fetched competitor text against the last stored snapshot."""
import difflib
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.parent
SNAPSHOTS_DIR = ROOT / "data" / "snapshots"

# Ignore noise below this fraction of change (dates, whitespace, ad copy churn).
MIN_CHANGE_FRACTION = 0.03


def load_snapshot(cid: str) -> Optional[str]:
    f = SNAPSHOTS_DIR / f"{cid}.txt"
    return f.read_text(encoding="utf-8") if f.exists() else None


def save_snapshot(cid: str, text: str) -> None:
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    (SNAPSHOTS_DIR / f"{cid}.txt").write_text(text, encoding="utf-8")


def diff_one(cid: str, new_text: str) -> dict:
    old_text = load_snapshot(cid)

    if old_text is None:
        # Never tracked before: the whole page is the "diff" worth drafting from.
        return {
            "cid": cid, "is_new": True, "changed": True,
            "diff": new_text, "new_text": new_text, "similarity": 0.0,
        }

    if old_text.strip() == new_text.strip():
        return {
            "cid": cid, "is_new": False, "changed": False,
            "diff": "", "new_text": new_text, "similarity": 1.0,
        }

    ratio = difflib.SequenceMatcher(None, old_text, new_text).ratio()
    diff_lines = list(difflib.unified_diff(
        old_text.splitlines(), new_text.splitlines(),
        fromfile=f"{cid}/previous", tofile=f"{cid}/current", lineterm="",
    ))
    return {
        "cid": cid,
        "is_new": False,
        "changed": ratio < (1 - MIN_CHANGE_FRACTION),
        "diff": "\n".join(diff_lines),
        "new_text": new_text,
        "similarity": ratio,
    }
