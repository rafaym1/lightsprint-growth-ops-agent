# Growth-Ops Agent

This keeps LightSprint's comparison page honest without anyone remembering to update it.

It applies LightSprint's own product mechanic -- an agent proposes the change, a human
approves it via a real PR, non-engineers can steer the result -- to LightSprint's own
growth content instead of product code.

## How it works

```
 .github/workflows/growth-ops-agent.yml   (cron + manual trigger)
              |
              v
   scripts/run_pipeline.py
      |         |          |            |
      v         v          v            v
   fetch  ->  diff   ->  draft   ->  open_pr
  (Playwright) (stdlib)  (Claude API)  (gh CLI)
```

1. **Fetch** (`scripts/fetch_snapshot.py`) -- for each competitor in
   `data/comparisons.json`, loads its tracked page with a headless browser and
   extracts the clean article text. A real browser, not `requests`: OpenAI's
   marketing site returns a 403 to a bare HTTP GET (confirmed with curl, even
   with a browser User-Agent header) but renders fine for an actual browser,
   so a plain HTTP scraper would silently fail on one of the three tracked
   pages.
2. **Diff** (`scripts/diff_snapshot.py`) -- compares the fresh text against
   the last snapshot in `data/snapshots/`. A page tracked for the first time
   counts as a change (there's a real comparison to draft, we just haven't
   captured it yet); otherwise only changes past a small noise threshold
   (~3%) count, so date stamps and ad copy churn don't trigger false
   positives.
3. **Draft** (`scripts/draft_update.py`) -- on a real change, calls the
   Claude API with the current comparison entry, the diff, and
   `scripts/style_guide.md` (a tone guide distilled from LightSprint's own
   site copy), and asks for a small, evidence-only rewrite of the two lines
   that describe the comparison. It's explicitly told to leave copy
   unchanged if the diff doesn't actually warrant a rewrite.
4. **Open PR** (`scripts/open_pr.py`) -- commits the updated
   `data/comparisons.json` and new snapshot(s) to a branch and opens a real
   PR via `gh pr create`, with the drafted rationale and the raw diff the
   crawler saw, in the PR body. Nothing merges automatically.

`site/index.html` is a static page that renders `data/comparisons.json`
directly -- the same file the agent edits -- so there's one real "comparison
page" this keeps current, not just a JSON blob.

## Why a real PR and not a direct commit

Same reason LightSprint's own product works this way: an agent proposing a
change and a human approving it via a PR preview is a stronger trust model
than an agent quietly rewriting the page. A marketer with zero Python
experience can review this PR exactly like they'd review any other content
change -- read the diff, read the rationale, merge or request edits.

## Setup

```bash
pip install -r requirements.txt
playwright install chromium
```

One secret is required, and it has to be set by a human -- an agent should
never handle its own API key:

```bash
gh secret set ANTHROPIC_API_KEY --repo <owner>/<repo>
```

(paste the key when prompted; nothing is echoed or logged)

No GitHub token needs to be created -- the workflow uses the Actions-provided
`GITHUB_TOKEN`, scoped to just this repo, with `contents: write` and
`pull-requests: write` permissions declared in the workflow file.

## Running it

```bash
# locally, against your own working copy
python scripts/run_pipeline.py

# or trigger the real Actions workflow on demand
gh workflow run growth-ops-agent.yml
gh run watch
```

The workflow also runs on a weekly cron (Monday 13:00 UTC) so it doesn't
depend on anyone remembering to run it.

## Scaling to all 9

LightSprint's real `/compare` page tracks nine tools across three categories
(coding agents/editors, planning tools, app builders). This repo seeds three
(Claude Code, Cursor, Codex) to keep the build demoable in a day; adding the
rest is one entry per competitor in `data/comparisons.json` -- the pipeline
is generic over the list, nothing else changes.

## Known limitations

- Text extraction (`trafilatura`) is tuned for article-shaped marketing
  pages, not pricing tables rendered as complex nested components -- a
  redesign of a tracked page could need a per-page extraction tweak.
- The LLM draft step trusts the style guide and prompt constraints to avoid
  fabricating claims; it's worth spot-checking early PRs before trusting the
  output on a wider set of competitors.
