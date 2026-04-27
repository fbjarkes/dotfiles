---
description: 'Lint and auto-fix Python files changed on the current branch vs a target branch'
argument-hint: <base-branch>
---
Run `black` and `ruff` on the Python files changed between the current branch and `$ARGUMENTS`.

Steps:
1. Run `git diff --name-only --diff-filter=ACMR origin/$ARGUMENTS...HEAD` to get the list of changed Python files (filter to `.py` files only)
2. If no Python files changed, report that and stop
3. Run `uv run black <changed files>` and show the output
4. Run `uv run ruff check --fix <changed files>` to auto-fix violations, show the output
5. Run `uv run ruff check --statistics <changed files>` to surface remaining violations by rule, show the output
6. Run `uv run ruff check --select ALL --diff <changed files>` (without fixing) to suggest additional improvements beyond the default ruleset

Summary section at the end:
- List files reformatted by black
- List violations auto-fixed by ruff, grouped by rule code with a plain-English label
- List remaining violations (from --statistics) with a brief explanation of each rule
- Suggest 2-3 highest-impact additional improvements from the --select ALL output, with the rule code, a plain-English explanation, and why it matters
