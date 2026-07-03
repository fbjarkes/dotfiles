---
allowed-tools: Bash(git status:*), Bash(git log:*), Bash(git diff:*), Bash(git branch:*), Bash(git rev-parse:*), Bash(gh pr list:*), Bash(gh pr view:*), Bash(gh pr edit:*)
argument-hint: [pr-number]
description: Sync an existing PR's body to reflect the latest code changes
---

## Context

- Current branch: !`git branch --show-current`
- HEAD commit: !`git rev-parse HEAD`
- HEAD commit time: !`git log -1 --format=%cI HEAD`
- Existing PRs for this branch: !`gh pr list --head "$(git branch --show-current)" --json number,title,url 2>/dev/null || echo "none"`
- Recent commits: !`git log --oneline -10`

## Your task

Update the body of an **existing** open PR so it reflects the current code changes. This command does not create, merge, or close PRs — for that use `/pull-request`.

Resolve the target PR from `$ARGUMENTS` (a PR number) if given, otherwise the open PR for the current branch. If none exists, stop and tell the user to run `/pull-request` first.

### The sync marker

The PR body carries a hidden marker recording the commit and time of the last body sync:

```
<!-- pr-sync: <commit-hash> @ <ISO-8601-timestamp> -->
```

This is the placeholder that drives incremental updates. `PULL_REQUEST_TEMPLATE.md` may already contain a `<!-- pr-sync: ... -->` line as a placeholder; if so, that is where the marker lives.

### Steps

1. Fetch the current PR body: `gh pr view <number> --json body -q .body`
2. Look for the `<!-- pr-sync: <hash> @ <time> -->` marker in the body:
   - **Marker found** — extract `<hash>`. If `<hash>` equals the current `HEAD` commit, there are no new commits: report "PR body already up to date" and stop. Otherwise scope the review to commits since that hash:
     `git log --oneline <hash>..HEAD` and `git diff <hash>..HEAD`
   - **No marker** (or the recorded hash is unknown to the repo, e.g. rebased away) — fall back to the full code change against the base branch:
     `git log --oneline origin/develop..HEAD 2>/dev/null || git log --oneline origin/main..HEAD 2>/dev/null` and the equivalent `git diff`
3. If the scoped range has no new commits, report that and stop.
4. Regenerate the body from the changes:
   - Read `PULL_REQUEST_TEMPLATE.md` from the repo root if present and keep its structure. Preserve any user-authored sections not derived from code (e.g. testing notes, checkboxes the author ticked).
   - Update the code-derived sections — summary bullets (2–5), and the "Implementation Plan (LLM only)" section if the template has one — to reflect the full current state of the branch, not just the incremental delta. Use the scoped range only to know *what changed since last sync* so you can revise efficiently; the resulting body should still describe the whole PR.
5. Check for a connected spec / PRD and whether it matches the current code state:
   - Look for a spec/PRD tied to this feature — a linked doc referenced in the PR body or commits, or a file under `specs/`, `docs/`, `prd/`, `.specs/` (or similar) matching the branch/feature name.
   - If one exists, compare its described behavior, scope, and interfaces against the current code changes (the scoped range, plus a full read of the spec).
   - **Do not modify the spec/PRD files.** If it is out of sync, add a clear warning to the PR body (e.g. under a "⚠️ Spec out of sync" heading) naming the spec file and explaining *why* — which requirements the code no longer matches, what was added beyond the spec, or what the spec still mandates that the code hasn't implemented. If they are in sync, note that briefly and add no warning.
6. Write a fresh marker line with the current `HEAD` hash and its commit time (from Context above), replacing any existing marker.
7. Apply the update: `gh pr edit <number> --body "<new-body>"`.
8. Report what changed: the commit range synced, the new marker hash/time, a one-line note of which sections you revised, and the spec sync verdict (in sync / out of sync + why / no spec found).

Respect the project PR guidelines from CLAUDE.md at all times.
