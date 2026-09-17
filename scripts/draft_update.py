#!/usr/bin/env python3
"""Draft updated comparison copy for a competitor whose tracked page changed.

Calls the Gemini API with the current entry, the house style guide, and the
detected diff, and asks for a small, honest rewrite -- never a wholesale
rewrite untethered from what actually changed.
"""
import json
import os
from pathlib import Path

from google import genai

ROOT = Path(__file__).parent.parent
STYLE_GUIDE = (ROOT / "scripts" / "style_guide.md").read_text(encoding="utf-8")

MODEL = "gemini-3.8-flash"

PROMPT_TEMPLATE = """You maintain LightSprint's competitor comparison page. Below is the \
current entry for "{name}", the style guide it must follow, and the {change_kind} in \
{name}'s own marketing copy that was just detected by an automated crawl.

Current entry (JSON):
{current_entry}

Style guide:
{style_guide}

{change_kind_upper} detected on {name}'s page ({url}):
{diff_text}

Task: rewrite `stronger_for` and `lightsprint_better_for` for this entry so they reflect \
{name}'s current, real positioning. Keep the same tone and sentence shape as the current \
entry. Do not invent features or pricing that aren't evidenced in the fetched text above. \
If, after reading the change, the existing copy is still accurate, keep it as-is rather \
than rewriting for the sake of it.

Respond with ONLY a JSON object, no markdown fences, no commentary:
{{"stronger_for": "...", "lightsprint_better_for": "...", "changelog_note": "one sentence \
for a PR description explaining what changed on their side and what, if anything, we \
updated and why"}}"""


_CLIENT: genai.Client | None = None


def _client() -> genai.Client:
    # Must be a long-lived singleton, not created-and-chained per call: the
    # SDK ties its underlying httpx client's lifecycle to the Client object,
    # and a bare temporary (`_client().models...`) gets torn down mid-request
    # ("RuntimeError: Cannot send a request, as the client has been closed").
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _CLIENT


def draft_for(entry: dict, diff_result: dict) -> dict:
    change_kind = "initial page capture" if diff_result["is_new"] else "change"
    prompt = PROMPT_TEMPLATE.format(
        name=entry["name"],
        change_kind=change_kind,
        change_kind_upper=change_kind.upper(),
        current_entry=json.dumps(entry, indent=2),
        style_guide=STYLE_GUIDE,
        url=entry["track_url"],
        diff_text=(diff_result["diff"] or diff_result["new_text"])[:6000],
    )
    resp = _client().models.generate_content(model=MODEL, contents=prompt)
    text = resp.text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0].strip()
        if text.startswith("json"):
            text = text[4:].strip()
    return json.loads(text)
