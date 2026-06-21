#!/usr/bin/env python3
"""Gather open-PR status signals via `gh` and emit a JSON triage report.

Deterministic data-gathering and scoring lives here so the calling agent doesn't
re-derive date math or re-run N+1 `gh` calls per PR. The agent is responsible for
turning the JSON into a markdown report and proposing (not executing) actions.
"""
import argparse
import difflib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone

PR_FIELDS = "number,title,headRefName,baseRefName,createdAt,updatedAt,isDraft,mergeable,reviewDecision,additions,deletions,changedFiles,author,url,files,commits"

TITLE_NOISE_RE = re.compile(r"^\[?(wip|stacked)\]?\s*[:\-]?\s*", re.IGNORECASE)
CONVENTIONAL_PREFIX_RE = re.compile(r"^(feat|fix|chore|docs|test|refactor|perf|build|ci)(\([^)]*\))?\s*:\s*", re.IGNORECASE)


def run_gh(args: list[str]) -> str:
    result = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    return result.stdout


def normalize_title(title: str) -> str:
    t = TITLE_NOISE_RE.sub("", title)
    t = CONVENTIONAL_PREFIX_RE.sub("", t)
    return t.strip().lower()


def fetch_open_prs() -> list[dict]:
    raw = run_gh(["pr", "list", "--state", "open", "--json", PR_FIELDS])
    return json.loads(raw)


def fetch_default_branch() -> str:
    raw = run_gh(["repo", "view", "--json", "defaultBranchRef"])
    data = json.loads(raw)
    return (data.get("defaultBranchRef") or {}).get("name", "main")


def fetch_owner_repo() -> tuple[str, str]:
    raw = run_gh(["repo", "view", "--json", "owner,name"])
    data = json.loads(raw)
    return data["owner"]["login"], data["name"]


def fetch_last_edited_map(owner: str, repo: str, pr_numbers: list[int]) -> dict[int, str | None]:
    """Body-edit timestamp per PR. `lastEditedAt` isn't in gh's --json field
    list for pr/list/view (only raw GraphQL exposes it), so this issues one
    batched query with a field alias per PR number instead of one gh call per
    PR."""
    if not pr_numbers:
        return {}
    aliases = "\n".join(f"pr{n}: pullRequest(number: {n}) {{ lastEditedAt }}" for n in pr_numbers)
    query = f"query($owner: String!, $repo: String!) {{ repository(owner: $owner, name: $repo) {{ {aliases} }} }}"
    try:
        raw = run_gh(["api", "graphql", "-f", f"query={query}", "-F", f"owner={owner}", "-F", f"repo={repo}"])
        repo_data = json.loads(raw)["data"]["repository"]
        return {n: repo_data[f"pr{n}"]["lastEditedAt"] for n in pr_numbers}
    except (RuntimeError, KeyError, TypeError):
        return {n: None for n in pr_numbers}


def fetch_ci_status(pr_number: int, head_branch: str) -> dict:
    """CI status for a PR. `gh pr checks` needs the Checks API; many fine-grained
    PATs lack that scope and it fails with 403. Fall back to the Actions API
    (`gh run list`) which uses a different, more commonly granted scope."""
    try:
        raw = run_gh(["pr", "checks", str(pr_number), "--json", "name,state"])
        checks = json.loads(raw)
        if not checks:
            return {"status": "none", "source": "pr_checks"}
        states = {c["state"] for c in checks}
        if "FAILURE" in states or "ERROR" in states:
            return {"status": "failure", "source": "pr_checks"}
        if "PENDING" in states or "IN_PROGRESS" in states:
            return {"status": "pending", "source": "pr_checks"}
        return {"status": "success", "source": "pr_checks"}
    except RuntimeError:
        pass

    try:
        raw = run_gh(["run", "list", "--branch", head_branch, "--limit", "1", "--json", "status,conclusion"])
        runs = json.loads(raw)
        if not runs:
            return {"status": "none", "source": "run_list"}
        run = runs[0]
        if run["status"] != "completed":
            return {"status": "pending", "source": "run_list"}
        return {"status": run["conclusion"] or "unknown", "source": "run_list"}
    except RuntimeError as e:
        return {"status": "unknown", "source": "error", "error": str(e)}


def days_since(iso_ts: str, now: datetime) -> int:
    dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    return (now - dt).days


def compute_body_staleness(pr: dict, last_edited_at: str | None, body_stale_days: int) -> dict:
    """Flag a PR whose description hasn't been touched since well after the
    latest commit landed. If the body was never edited, GitHub returns
    lastEditedAt = null, so fall back to createdAt — an untouched body next to
    many post-creation commits is exactly the case worth flagging."""
    commits = pr.get("commits") or []
    if not commits:
        return {"last_edited_at": last_edited_at, "last_commit_at": None, "gap_days": None, "stale": False}

    last_commit_at = max(c["committedDate"] for c in commits)
    effective_edit_at = last_edited_at or pr["createdAt"]

    edit_dt = datetime.fromisoformat(effective_edit_at.replace("Z", "+00:00"))
    commit_dt = datetime.fromisoformat(last_commit_at.replace("Z", "+00:00"))
    gap_days = (commit_dt - edit_dt).days

    return {
        "last_edited_at": last_edited_at,
        "last_commit_at": last_commit_at,
        "gap_days": gap_days,
        "stale": gap_days >= body_stale_days,
    }


def find_stacked_on(pr: dict, head_branch_to_number: dict[str, int]) -> int | None:
    return head_branch_to_number.get(pr["baseRefName"])


def find_duplicates(prs: list[dict], stacked_pairs: set[tuple[int, int]]) -> dict[int, list[dict]]:
    """Pairwise compare open PRs on title similarity + changed-file overlap.
    Stacked pairs (one PR's base == another's head) are excluded: overlapping
    files there is expected (the later PR builds on the earlier one), not a sign
    of duplicated work."""
    duplicates: dict[int, list[dict]] = {}
    for i, pr_a in enumerate(prs):
        files_a = {f["path"] for f in pr_a.get("files", [])}
        title_a = normalize_title(pr_a["title"])
        for pr_b in prs[i + 1 :]:
            pair = (pr_a["number"], pr_b["number"])
            if pair in stacked_pairs or (pair[1], pair[0]) in stacked_pairs:
                continue
            title_b = normalize_title(pr_b["title"])
            title_sim = difflib.SequenceMatcher(None, title_a, title_b).ratio() if title_a and title_b else 0.0

            files_b = {f["path"] for f in pr_b.get("files", [])}
            if files_a and files_b:
                file_overlap = len(files_a & files_b) / len(files_a | files_b)
            else:
                file_overlap = 0.0

            if title_sim >= 0.6 or file_overlap >= 0.5:
                entry = {"number": pr_b["number"], "title_similarity": round(title_sim, 2), "file_overlap": round(file_overlap, 2)}
                duplicates.setdefault(pr_a["number"], []).append(entry)
                entry_rev = {"number": pr_a["number"], "title_similarity": round(title_sim, 2), "file_overlap": round(file_overlap, 2)}
                duplicates.setdefault(pr_b["number"], []).append(entry_rev)
    return duplicates


def recommend(pr: dict, age_days: int, inactive_days: int, stale_days: int, ci: dict, stacked_on: int | None, dup_of: list[dict]) -> dict:
    n = pr["number"]
    branch = pr["headRefName"]
    base = pr["baseRefName"]
    is_stale = inactive_days >= stale_days

    if pr["isDraft"] and is_stale:
        return {
            "action": "close-or-confirm",
            "reason": f"Draft, no activity for {inactive_days}d",
            "steps": [f'gh pr comment {n} --body "Still working on this? Will close if no update in 7 days."', f"gh pr close {n}  # if confirmed abandoned"],
        }
    if pr["isDraft"]:
        return {"action": "no-action", "reason": "Draft, still in progress", "steps": []}

    if dup_of:
        others = ", ".join(f"#{d['number']}" for d in dup_of)
        return {
            "action": "resolve-duplicate",
            "reason": f"Overlaps with {others} (title/file similarity)",
            "steps": [f"gh pr diff {n} > /tmp/pr{n}.diff", f"gh pr diff {dup_of[0]['number']} > /tmp/pr{dup_of[0]['number']}.diff", "# compare diffs, close the redundant one"],
        }

    if pr["mergeable"] == "CONFLICTING":
        return {
            "action": "needs-rebase",
            "reason": "Merge conflicts against base branch",
            "steps": [f"git fetch origin", f"git checkout {branch}", f"git rebase origin/{base}", "# resolve conflicts, then: git push --force-with-lease"],
        }

    if ci["status"] == "failure":
        return {"action": "fix-ci", "reason": "CI failing", "steps": [f"gh run list --branch {branch} --limit 1", f"gh pr checks {n}  # or inspect failing job logs"]}

    if pr["reviewDecision"] == "CHANGES_REQUESTED":
        return {"action": "needs-author-response", "reason": "Reviewer requested changes", "steps": [f"gh pr view {n} --comments"]}

    if stacked_on:
        return {
            "action": "no-action",
            "reason": f"Stacked on #{stacked_on} — wait for base PR to merge first",
            "steps": [],
        }

    if pr["reviewDecision"] == "APPROVED" and ci["status"] in ("success", "none") and pr["mergeable"] == "MERGEABLE":
        return {"action": "ready-to-merge", "reason": "Approved, CI green, no conflicts", "steps": [f"gh pr merge {n} --squash"]}

    if is_stale:
        return {
            "action": "stale-confirm-or-close",
            "reason": f"No activity for {inactive_days}d (threshold {stale_days}d)",
            "steps": [f'gh pr comment {n} --body "Is this still needed? Will close if no update in 7 days."', f"gh pr close {n}  # if confirmed abandoned"],
        }

    if not pr["reviewDecision"]:
        return {"action": "needs-review", "reason": "No review yet", "steps": [f"gh pr edit {n} --add-reviewer <reviewer>"]}

    return {"action": "active", "reason": "Recently active, no signal to act on", "steps": []}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stale-days", type=int, default=30, help="Inactivity threshold (days) to flag a PR as stale")
    parser.add_argument("--skip-ci", action="store_true", help="Skip CI status lookups (faster, no extra gh calls)")
    parser.add_argument("--body-stale-days", type=int, default=7, help="Days a PR body can lag behind its latest commit before being flagged stale")
    parser.add_argument("--skip-body-staleness", action="store_true", help="Skip body-staleness check (saves one gh api graphql call)")
    args = parser.parse_args()

    now = datetime.now(timezone.utc)

    try:
        prs = fetch_open_prs()
    except RuntimeError as e:
        print(json.dumps({"error": f"failed to list open PRs: {e}"}), file=sys.stderr)
        sys.exit(1)

    if not prs:
        print(json.dumps({"prs": [], "default_branch": None}))
        return

    default_branch = fetch_default_branch()
    head_branch_to_number = {pr["headRefName"]: pr["number"] for pr in prs}

    if args.skip_body_staleness:
        last_edited_map: dict[int, str | None] = {pr["number"]: None for pr in prs}
    else:
        owner, repo = fetch_owner_repo()
        last_edited_map = fetch_last_edited_map(owner, repo, [pr["number"] for pr in prs])

    stacked_pairs: set[tuple[int, int]] = set()
    for pr in prs:
        stacked_on = find_stacked_on(pr, head_branch_to_number)
        if stacked_on:
            stacked_pairs.add((pr["number"], stacked_on))

    duplicates = find_duplicates(prs, stacked_pairs)

    report = []
    for pr in prs:
        age_days = days_since(pr["createdAt"], now)
        inactive_days = days_since(pr["updatedAt"], now)
        ci = {"status": "skipped", "source": "skipped"} if args.skip_ci else fetch_ci_status(pr["number"], pr["headRefName"])
        stacked_on = find_stacked_on(pr, head_branch_to_number)
        dup_of = duplicates.get(pr["number"], [])
        if args.skip_body_staleness:
            body_staleness = {"skipped": True}
        else:
            body_staleness = compute_body_staleness(pr, last_edited_map.get(pr["number"]), args.body_stale_days)

        rec = recommend(pr, age_days, inactive_days, args.stale_days, ci, stacked_on, dup_of)

        report.append(
            {
                "number": pr["number"],
                "title": pr["title"],
                "url": pr["url"],
                "author": pr["author"]["login"],
                "head": pr["headRefName"],
                "base": pr["baseRefName"],
                "is_draft": pr["isDraft"],
                "age_days": age_days,
                "inactive_days": inactive_days,
                "mergeable": pr["mergeable"],
                "review_decision": pr["reviewDecision"] or None,
                "ci": ci,
                "stacked_on": stacked_on,
                "duplicate_of": dup_of,
                "body_staleness": body_staleness,
                "recommendation": rec,
            }
        )

    print(
        json.dumps(
            {
                "default_branch": default_branch,
                "stale_threshold_days": args.stale_days,
                "body_stale_threshold_days": args.body_stale_days,
                "prs": report,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
