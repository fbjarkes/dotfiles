---
user-invocable: true
description: 'Run linting tools on changeset and provide feedback, e.g use "run with develop"'
tools: ['execute', 'read', 'edit', 'search', 'web', 'agent', 'todo',]
---
Unless specified, use current branch as <SOURCE_BRANCH> and develop as <TARGET_BRANCH>.
You should create a change set between the <SOURCE_BRANCH> and the <TARGET_BRANCH> to identify which files have been modified. This can be done using git commands like `git diff <TARGET_BRANCH>...<SOURCE_BRANCH> --name-only` to get a list of modified files.

Before running formatters/linters, perform an environment preflight so the agent can recover from errors like `/bin/bash: uv: command not found`:
- Check whether `uv` exists (`command -v uv`).
- If `uv` is available, run linting/formatting through Makefile targets.
- If `uv` is not available, check whether `.venv/bin/uv` exists and temporarily prepend `.venv/bin` to `PATH` before running Makefile targets.
- If `uv` is missing both globally and in `.venv/bin`, do not proceed with broad formatting/linting changes. Report a clear blocker with exact missing commands and the smallest recommended fix (for example: install `uv` or create/sync `.venv`).

Specifically allowed direct command patterns (when operating on only files in the changeset):
- `uv run ruff ...`
- `uv run black ...`


The intention is to run linting tools on only modified files within the changeset.

Only run linting tools on files that are modified within the changeset. This ensures that you are not making formatting or linting changes to files that were not modified by the developer, which could create noise in the pull request and make it harder for reviewers to focus on the actual changes made by the developer.

Important: do not run on all files!

For the changeset in question, run these subagents sequentially:
- python-black-formatter
- python-ruff-formatter

After all subagents complete, summarize changes made and any remaining issues. Note which issues are critical versus nice-to-have.



