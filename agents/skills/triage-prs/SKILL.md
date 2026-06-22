---
name: triage-prs
description: Triage open GitHub PRs for the current repo — fetch every open PR via gh, score each one for staleness, merge conflicts, CI status, review state, draft status, duplicate/overlapping work, and stacked-PR chains, then produce a markdown (default) or standalone HTML report with a recommended next action and concrete (unexecuted) command steps per PR. Use whenever the user asks to "triage PRs", "do PR triage", "review open PRs", "clean up stale PRs", "what should I do with these PRs", or runs a daily/periodic PR review. Works in any git repo with a GitHub remote and an authenticated `gh` CLI.
---

# Triage PRs

Drives `driver.py` to gather PR status signals deterministically, then you (the
agent) turn that JSON into a markdown triage report. Do not hand-roll the `gh`
calls yourself — the script handles a real `gh` permission gotcha (see
Troubleshooting) and the stacked-PR / duplicate-detection logic that's easy to
get wrong by eye.

## Prerequisites

- `gh` CLI installed and authenticated (`gh auth status`).
- Run from inside the target git repo (the script uses the repo's `gh` context,
  no `--repo` flag needed).
- Python 3 (stdlib only, no pip installs required).

## Run

```bash
python3 ~/.claude/skills/triage-prs/driver.py
```

Optional flags:

- `--stale-days N` — inactivity threshold for flagging a PR as stale (default 30).
- `--skip-ci` — skip CI lookups (faster; `ci.status` becomes `"skipped"`).
- `--body-stale-days N` — how many days a PR's body can lag behind its latest
  commit before being flagged stale (default 7).
- `--skip-body-staleness` — skip the body-staleness check (one fewer `gh api
  graphql` call; `body_staleness` becomes `{"skipped": true}`).
- `--format {markdown,html}` — report type to produce (default `markdown`).
  `markdown` leaves report authoring to you, the calling agent (see "Build the
  report" below). `html` has the script render a complete, styled, standalone
  HTML report deterministically and write it to disk — don't hand-author the
  HTML yourself, see "HTML format" below.
- `--output PATH` — only used with `--format html`; where to write the report
  file (default `./pr-triage-report.html`).

Output is JSON on stdout: `{"default_branch": ..., "stale_threshold_days": ...,
"format": ..., "report_file": ..., "prs": [...]}`. Each PR entry has
`recommendation: {action, reason, steps}` — `steps` is a list of `gh`/`git`
commands that *would* resolve the situation. **Never execute these
automatically.** Present them in the report; let the user decide and run them
(or explicitly ask you to run a specific one).

## Build the report

Applies when `--format markdown` (the default) was used. `report_file` will be
`null` — there's nothing on disk to point to, the report only exists in your
reply.

Group PRs by `recommendation.action` into sections, most actionable first:

1. `ready-to-merge`
2. `needs-rebase`
3. `fix-ci`
4. `needs-author-response`
5. `resolve-duplicate`
6. `stale-confirm-or-close` / `close-or-confirm`
7. `needs-review`
8. `active` / `no-action`

For each PR show: `#number title (author)`, age/inactivity in days, and the
`reason`. Under each section, list the proposed `steps` as a fenced code block
so the user can copy-paste if they agree. If `stacked_on` is set, note it
inline (e.g. "stacked on #98 — wait for base to merge") regardless of which
section the PR landed in.

If `duplicate_of` is non-empty for a PR, name the other PR(s) and mention
whether the signal was title similarity, file overlap, or both — let the user
make the close/keep call, don't pick for them.

If `body_staleness.stale` is `true`, add a note under that PR regardless of
which section it landed in — e.g. "description last edited N days before the
latest commit, may not reflect current state". This isn't its own action
bucket (an out-of-date body doesn't block a merge the way a conflict does);
it's a heads-up so the user knows to skim the diff instead of trusting the
description. Don't surface this note when `body_staleness` is `{"skipped":
true}` or when `stale` is `false`.

## HTML format

Applies when `--format html` was used. The script already wrote the full
report — same section order, same per-PR notes (stacked, duplicate,
body-staleness) — to the path in `report_file`. Don't re-render it in
markdown or re-derive the sections yourself. Just tell the user the file path
and give a one- or two-sentence summary (e.g. counts per section, anything
urgent like a draft about to be closed). If they want to view it, suggest
opening it in a browser.

## Gotchas

- **`gh pr checks` / the REST check-runs endpoint often 403s** with
  `Resource not accessible by personal access token` — fine-grained PATs
  frequently lack the Checks-API scope even when `gh auth status` shows a
  valid login. The script automatically falls back to `gh run list --branch
  <head> --limit 1` (Actions API, a different scope that's almost always
  granted) and tags the result with `ci.source` so you know which path was
  used. If you see `ci.status: "unknown"` with `source: "error"`, both paths
  failed — say so in the report rather than guessing CI state.
- **File-overlap alone overcounts stacked PRs as duplicates.** A PR whose
  `baseRefName` is another open PR's `headRefName` (a "stacked" PR, per this
  kind of repo's `[stacked]` naming convention) will legitimately share
  changed files with its base PR. The script excludes stacked pairs from
  duplicate detection — don't re-flag them yourself by eye.
- **`mergeable` is sometimes `"UNKNOWN"`** — GitHub computes it
  asynchronously and hasn't finished for that PR yet. Don't treat `UNKNOWN` as
  "no conflicts"; report it as "conflict status not yet computed by GitHub,
  re-check shortly" rather than assuming clean.
- **Draft PRs short-circuit other signals.** A draft with merge conflicts and
  failing CI isn't "needs-rebase" or "fix-ci" — it's just a draft, those
  signals don't matter until it's marked ready. The script checks draft+stale
  first, draft-not-stale second, before any other rule.
- **`lastEditedAt` isn't in `gh`'s `--json` field list** for `pr list`/`pr
  view` — only raw GraphQL exposes it, which is why the script issues one
  `gh api graphql` call with a field alias per PR number (not one call per
  PR) to fetch it for everyone in a single round trip. GitHub returns `null`
  if the body was never edited after creation, so the script falls back to
  `createdAt` in that case — an untouched body next to many post-creation
  commits is exactly the case worth flagging, not a reason to skip it.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `failed to list open PRs: failed to run git: fatal: not a git repository` | Run from inside the target repo's working directory. |
| `gh: command not found` | Install the GitHub CLI (`apt install gh` / `brew install gh`) and run `gh auth login`. |
| All PRs show `ci.status: "unknown"` | Both `gh pr checks` and `gh run list` failed — check `gh auth status` token scopes, or the repo may have no Actions workflows at all (then `"none"` is correct, not `"unknown"`). |
| Report shows a duplicate pair that's actually a deliberate stack | Check `stacked_on` in the JSON — if it's `null` for both but they share a base ref and similar titles, it may be a real duplicate; if `stacked_on` is set, the script already excluded it from `duplicate_of` and something else triggered the similarity (rare false positive, flag manually). |
