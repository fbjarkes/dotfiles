---
allowed-tools: Bash(git status:*), Bash(git log:*), Bash(git diff:*), Bash(git branch:*), Bash(git push:*), Bash(gh pr create:*), Bash(gh pr list:*), Bash(gh pr view:*), Bash(gh pr merge:*), Bash(gh pr close:*), Bash(gh pr checkout:*), Bash(gh pr edit:*)
argument-hint: [create|list|view|merge|close] [pr-number]
description: Create and manage GitHub pull requests
---

## Context

- Current branch: !`git branch --show-current`
- Current git status: !`git status`
- Commits ahead of main branch: !`git log --oneline origin/develop..HEAD 2>/dev/null || git log --oneline origin/main..HEAD 2>/dev/null`
- Existing PRs for this branch: !`gh pr list --head "$(git branch --show-current)" 2>/dev/null || echo "none"`
- Recent commits: !`git log --oneline -10`

## Your task

The user may pass an action via `$ARGUMENTS`:
- **create** (default if no PR exists): Create a new pull request for the current branch
- **list**: List open pull requests
- **view [number]**: Show details of a PR
- **merge [number]**: Merge a PR
- **close [number]**: Close a PR without merging

### Creating a PR

When creating a PR:
1. Read `PULL_REQUEST_TEMPLATE.md` if it exists in the repo root and use it as the body template
2. Determine the base branch (default: `develop`, fallback `main`)
3. Derive the PR title from the branch name following conventional commits:
   - `feature/add-my-feature` → `feat: add my feature`
   - `fix/update-unittests` → `fix: update unittests`
   - `copilot/add-my-feature` → `feat: add my feature`
   - Add `[stacked]` prefix if the base branch is NOT `develop` or `main`
4. Summarize all commits since the base branch into a concise body (2–5 bullet points)
5. Fill in the "Implementation Plan (LLM only)" section of the template if present
6. Push the branch to origin if not already pushed (`git push -u origin <branch>`)
7. Create the PR with `gh pr create`

### Managing existing PRs

For list/view/merge/close, use the appropriate `gh pr` subcommand with the provided PR number.

Respect the project PR guidelines from CLAUDE.md at all times.
