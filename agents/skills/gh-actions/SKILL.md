---
name: gh-actions-skill
description: Retrieve GitHub Actions workflow execution details including status, job information, logs, and run metrics. Use this when you need to monitor CI/CD pipelines, troubleshoot failed workflows, analyze job performance, identify bottlenecks, or get detailed run information to debug build issues.
---

# GitHub Actions Skill

## Quick Start

The GitHub CLI (`gh`) provides direct access to workflow and job information. All commands assume you're in a repository directory.

### Get latest workflow runs
```bash
gh run list --limit 10
```
Output shows: status (✓ pass, ✗ fail, ⏸ queued), title, workflow name, branch, event type, run ID, and duration.

### Check specific workflow status
```bash
gh run list --workflow Python\ CI --limit 5
```

### Get detailed run information
```bash
gh run view <RUN_ID>
```

## Common Workflows

### 1. Monitor Recent Runs and Identify Failures

**Scenario:** You want to see which runs failed and what branch they're on.

```bash
# Get last 15 runs with status indicators
gh run list --limit 15

# Filter to just failed runs
gh run list --status failed --limit 10

# Get failed runs for a specific workflow
gh run list --workflow "Python CI" --status failed --limit 5
```

**Interpreting output:**
- `✓` = successful
- `✗` = failed
- `⏸` = queued or in progress
- Column headers: STATUS | TITLE | WORKFLOW | BRANCH | EVENT | ID | ELAPSED | AGE

### 2. Debug a Specific Failed Run

**Scenario:** A workflow run failed and you need to understand why.

```bash
# View full run details including conclusion and annotations
gh run view <RUN_ID>

# Get job details for the run
gh run view <RUN_ID> --json jobs

# See which jobs failed
gh run view <RUN_ID> --json jobs --jq '.jobs[] | select(.conclusion=="failure") | {name, conclusion, databaseId}'
```

### 3. Retrieve Job Logs for Troubleshooting

**Scenario:** A specific job failed and you need to see the error messages.

```bash
# Download and view full logs for a run
gh run view <RUN_ID> --log

# Get logs for a specific job
gh run view <RUN_ID> --log-failed

# Save logs to a file for analysis
gh run view <RUN_ID> --log > run_logs.txt
```

**Key points:**
- `--log` displays all job logs in the terminal
- `--log-failed` shows only failed job logs (faster for large runs)
- Logs are most useful when troubleshooting test failures, dependency issues, or runtime errors

### 4. Analyze Job Performance

**Scenario:** You want to identify which jobs are slow or consistently timing out.

```bash
# Get detailed job timing for a run
gh run view <RUN_ID> --json jobs --jq '.jobs[] | {name, status, conclusion, startedAt, completedAt}'

# Compare elapsed times across multiple runs
gh run list --workflow "Python CI" --limit 5 --json id,startedAt,databaseId,durationMinutes

# Find longest-running job
gh run view <RUN_ID> --json jobs --jq '.jobs | max_by(.durationMinutes)'
```

### 5. Inspect Workflow Configuration

**Scenario:** You need to understand what a workflow does without leaving the terminal.

```bash
# List all workflows
gh workflow list

# View specific workflow file
gh workflow view <WORKFLOW_ID>

# Get workflow details in JSON
gh workflow view <WORKFLOW_ID> --json triggers,path
```

## Advanced Patterns

### Programmatic Run Status Check

When you need to poll run status (useful in automation):

```bash
# Get run status as JSON
gh run view <RUN_ID> --json status,conclusion,databaseId

# Check if run is complete
gh run view <RUN_ID> --json conclusion --jq '.conclusion != null'
```

### Get Run Information for Latest PR

```bash
# Get the latest run for your current branch
gh run list --branch $(git rev-parse --abbrev-ref HEAD) --limit 1

# Get full details of latest run
gh run view $(gh run list --limit 1 --json databaseId --jq '.[0].databaseId') --json status,conclusion,createdAt,updatedAt
```

### Filter Runs by Event Type

```bash
# Show only push events
gh run list --event push --limit 10

# Show only pull request events
gh run list --event pull_request --limit 10

# Show scheduled runs
gh run list --event schedule --limit 10
```

## Key Fields Explained

| Field | Meaning | Example |
|-------|---------|---------|
| **status** | Current state | `completed`, `queued`, `in_progress` |
| **conclusion** | Final outcome | `success`, `failure`, `neutral`, `cancelled`, `timed_out` |
| **durationMinutes** | Total elapsed time | `1`, `53` |
| **createdAt** | When run started | `2025-12-14T10:30:00Z` |
| **event** | What triggered run | `push`, `pull_request`, `schedule` |

## Best Practices

1. **Use `--json` for parsing**: Always use `--json --jq` for scripting to avoid relying on text parsing
2. **Limit results**: Use `--limit` to avoid overwhelming output; start with 5-10 runs
3. **Filter early**: Use `--status`, `--workflow`, `--branch` to narrow down results before viewing logs
4. **Save large logs**: Redirect logs to files (`> file.txt`) before analysis
5. **Check conclusion, not status**: For final results, check `conclusion` field, not `status` (status tells current state, conclusion tells result)