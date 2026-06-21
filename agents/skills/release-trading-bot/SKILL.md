---
name: release-trading-bot
description: trading-bot release workflow. Use when user asks to "do a release", "release a new version", or "cut a release" for the trading-bot Python project. Builds a release commit on develop (version bump + changelog) and squash-merges develop into main as a single release commit.
---

# Release Workflow (trading-bot)

A release here is: bump the version, update the changelog, commit that on
`develop`, then squash-merge `develop` into `main` as a single commit. No PR,
no CI publish step — just two branches and a tag.

`main` is kept to one commit per release on purpose: each commit on `main` is
a rollback unit, so `git revert`/`git checkout` against `main` always lands
on a clean release boundary instead of a mid-release state.

This is a GitFlow-lite / trunk-based hybrid — no single industry-standard
name for it, but it's recognizable as a **squash-merge release train**
("main as a tape of releases"): `develop` carries full commit history like
GitFlow's `develop`, but there are no `release/*` or hotfix branches and no
PRs; `main`'s log is curated 1:1 with `CHANGELOG.md`, one entry per shipped
version.

## Steps

1. **Sync `develop`**: make sure local `develop` matches the remote tip before
   cutting anything from it.
   ```bash
   git checkout develop
   git fetch origin
   git merge --ff-only origin/develop
   ```
   `--ff-only` fails loudly if `develop` has diverged from `origin/develop`
   instead of silently merging or dropping work — reconcile manually if it
   fails.
2. **Run tests**: `pytest` (adjust if the project uses `tox`/`nox`).
3. **Check current version**: read the version field (`pyproject.toml`
   `[project] version`, or `__version__` in the package's `__init__.py` —
   check which one this repo actually uses).
4. **Review commits since the last release**:
   ```bash
   git log v<last-version>..HEAD --oneline
   ```
   Skim the actual diffs for anything commit messages undersell, the same as
   you would for a changelog — don't trust the message alone.
5. **Determine release type** (patch/minor/major, semver): bug fixes only →
   patch; new backward-compatible features → minor; breaking changes →
   major. Ask the user only if genuinely ambiguous — don't ask when only one
   level is plausible.
6. **Bump the version**: edit the version field directly (or use
   `bump-my-version`/`hatch version` if the project already has one
   configured — check before introducing a new tool).
7. **Update `CHANGELOG.md`**: add a `## [X.Y.Z] - YYYY-MM-DD` section.
   Group entries as Added / Changed / Fixed (skip empty groups). Keep bullets
   to 1–2 sentences, describe the user-visible behavior, not the
   implementation. Skip pure-internal refactors and test-only commits.
8. **Commit the release** on `develop` — version bump and changelog land in a
   single commit:
   ```bash
   git add -A && git commit -m "chore(release): vX.Y.Z"
   ```
   `chore(release):` follows the Conventional Commits convention used by
   semantic-release/commitlint-style tooling — `chore` signals "no behavior
   change of its own," distinct from the `feat`/`fix` commits the release
   bundles. Use this form unless the user has an established convention
   already in their commit history; check `git log --oneline -20` first and
   match it if one exists.
9. **Push `develop`** — `git push` is user-run, not agent-run (see Notes):
   ```bash
   git push origin develop
   ```
10. **Squash-merge into `main`** — do the checkout/fetch/squash/commit steps
    yourself, but leave the push to the user:
    ```bash
    git checkout main
    git fetch origin
    git merge --ff-only origin/main   # make sure local main isn't behind
    git merge --squash develop
    git commit -m "chore(release): vX.Y.Z" -m "$(sed -n '/^## \[X.Y.Z\]/,/^## \[/p' CHANGELOG.md | sed '1d;$d')"
    git push origin main
    ```
    Commit message is the release title plus the same Added/Changed/Fixed
    body from the `CHANGELOG.md` entry for this version — `main`'s log
    should be readable on its own without cross-referencing `develop`.
    `git merge --squash` stages develop's changes without committing or
    advancing `main`'s parent — `main`'s history stays linear, one commit per
    release, instead of inheriting every individual `develop` commit.
11. **Tag the release** — create the tag locally, but the push is user-run:
    ```bash
    git tag vX.Y.Z && git push origin vX.Y.Z
    ```
12. **Return to `develop`** for continued work:
    ```bash
    git checkout develop
    ```
13. **If a tag-triggered CI workflow exists** (e.g. publishing to PyPI or
    deploying the bot), check its run status rather than assuming it
    succeeded:
    ```bash
    gh run list --branch=vX.Y.Z --limit 1
    ```
    Skip this step if no such workflow exists in this repo.

## Notes

- **All `git push` commands (steps 9, 10, 11) require manual user
  confirmation/execution in this environment** — `git push` is treated as a
  risky, shared-state action and gets denied when the agent runs it
  directly. Do every other step (commit, checkout, fetch, merge --ff-only,
  tag creation) yourself, then hand the exact `git push` commands to the
  user to run themselves rather than retrying the call.
- No PR is opened — `develop` → `main` goes straight through `git merge
  --squash`, so there's no drift window to re-check afterward the way a
  PR-based flow would have.
- If `git merge --ff-only origin/main` in step 10 ever fails, someone
  committed directly to `main` outside the release flow. Treat that as a
  process bug worth raising with the user, not something to silently work
  around with a merge commit.
- `git merge --squash develop` never fails the way `--ff-only` does — it
  just stages whatever's different. Diff what's staged against the commits
  you reviewed in step 4 before committing, so an unexpected direct commit
  to `main` doesn't get silently absorbed into the squash instead of
  surfacing as a conflict.
- v0.2.0 (the first release after this skill was written) was fast-forwarded
  rather than squashed — squash starts with the release after that. `main`'s
  log will have one inherited multi-commit "release" before the squashed
  ones begin.
