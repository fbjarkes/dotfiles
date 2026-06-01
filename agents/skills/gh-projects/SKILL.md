---
name: gh-projects-skill
description: Manage GitHub Projects and Issues from the CLI, including listing project issues, updating issue metadata, changing issue state, assigning users, and linking development branches.
---

# GitHub Projects + Issues Skill

## Quick Start

The GitHub CLI (`gh`) supports both Issues and Projects. Most workflows below assume you are in a repository directory.

Projects operations require the `project` scope on your token.

```bash
# Check current auth and scopes
gh auth status

# Add project scope if missing
gh auth refresh -s project
```

### List projects for an owner
```bash
gh project list --owner <OWNER> --limit 20
```

### List issues in a repository
```bash
gh issue list --state open --limit 30
```

### View items in a project
```bash
gh project item-list <PROJECT_NUMBER> --owner <OWNER> --limit 50
```

## Common Workflows

### 1. Discover Projects and Project Items

**Scenario:** You need to find the right project and inspect what issues are in it.

```bash
# List open projects for an org or user
gh project list --owner <OWNER> --limit 20

# View project details
gh project view <PROJECT_NUMBER> --owner <OWNER>

# List project items (table output)
gh project item-list <PROJECT_NUMBER> --owner <OWNER> --limit 100
```

### 2. List Issues for a Project (JSON filtering)

**Scenario:** You want issue-only rows from a project, not draft items.

```bash
# Dump project items as JSON
gh project item-list <PROJECT_NUMBER> --owner <OWNER> --format json

# Show issue-like content summary (adjust jq filter as needed for your schema)
gh project item-list <PROJECT_NUMBER> --owner <OWNER> --format json --jq '.items[] | select(.content.number != null) | {issue: .content.number, title: .content.title, state: .content.state, url: .content.url}'
```

**Tip:** Project item JSON can differ slightly by item type (issue, PR, draft). Start with raw JSON, then tighten your `--jq` filter.

### 3. Update Issue Title and Description

**Scenario:** You want to refine issue details without using the web UI.

```bash
# Update title and body
gh issue edit 123 --title "Clarify retry strategy" --body "Updated description with acceptance criteria"

# Update body from file
gh issue edit 123 --body-file docs/issue-123-body.md
```

### 4. Change Issue State (close/reopen)

**Scenario:** Mark work complete, or reopen for follow-up.

```bash
# Close with optional reason and comment
gh issue close 123 --reason completed --comment "Implemented in #456"

# Reopen
gh issue reopen 123
```

### 5. Assign Users, Labels, Milestones

**Scenario:** Keep ownership and triage metadata current.

```bash
# Assign users
gh issue edit 123 --add-assignee alice,bob

# Assign yourself
gh issue edit 123 --add-assignee "@me"

# Add and remove labels
gh issue edit 123 --add-label "bug,priority:high" --remove-label "needs-triage"

# Set milestone
gh issue edit 123 --milestone "v1.4"
```

### 6. Add/Remove Issues from a Project by Title

**Scenario:** Move an issue into or out of a project from the CLI.

```bash
# Add issue to project by project title
gh issue edit 123 --add-project "Roadmap"

# Remove issue from project
gh issue edit 123 --remove-project "Roadmap"
```

### 7. Update Project Item Fields (Status, Iteration, etc.)

**Scenario:** Move a project item from "Todo" to "In Progress" or set a date field.

```bash
# 1) Get project and field metadata
gh project view <PROJECT_NUMBER> --owner <OWNER> --format json
gh project field-list <PROJECT_NUMBER> --owner <OWNER> --format json

# 2) Get item IDs
gh project item-list <PROJECT_NUMBER> --owner <OWNER> --format json

# 3) Update one field value on one item (single-select example)
gh project item-edit \
  --id <ITEM_ID> \
  --project-id <PROJECT_ID> \
  --field-id <FIELD_ID> \
  --single-select-option-id <OPTION_ID>

# 4) Update a text field
gh project item-edit --id <ITEM_ID> --project-id <PROJECT_ID> --field-id <FIELD_ID> --text "Needs review"

# 5) Clear a field
gh project item-edit --id <ITEM_ID> --project-id <PROJECT_ID> --field-id <FIELD_ID> --clear
```

**Key constraint:** For non-draft issues, `gh project item-edit` updates one field per invocation.

### 8. Link Development Branches to Issues

**Scenario:** Create or view linked branches for an issue.

```bash
# List linked branches
gh issue develop --list 123

# Create a linked branch from default base
gh issue develop 123

# Create and check out linked branch
gh issue develop 123 --checkout

# Create linked branch from a specific base
gh issue develop 123 --base develop --checkout
```

### 9. Connect Pull Requests to Issues

**Scenario:** Ensure issue closes automatically when the PR merges.

```bash
# Create PR that auto-closes the issue on merge
gh pr create --title "Fix retry backoff" --body "Closes #123"
```

You can also use keywords like `Fixes #123` or `Resolves #123` in the PR body or commit message.

## Advanced Patterns

### Query issues with project context

```bash
gh issue list --state all --json number,title,state,projectItems --jq '.[] | {number, title, state, projects: [.projectItems[].project.title]}'
```

### Filter by assignee, labels, and search

```bash
gh issue list --assignee "@me" --label bug --state open --limit 50
gh issue list --search "is:open label:bug sort:updated-desc" --limit 50
```

### Multi-repo targeting

```bash
# Run against a different repository
gh issue list --repo <OWNER>/<REPO> --state all
```

## Key Fields Explained

| Field | Meaning | Example |
|-------|---------|---------|
| **project number** | Human-facing project ID in owner scope | `1` |
| **project id** | Internal GraphQL node ID for item edits | `PVT_kw...` |
| **item id** | Internal project item ID | `PVTI_lA...` |
| **field id** | Internal field ID (Status, Iteration, Date, etc.) | `PVTSSF_...` |
| **single-select option id** | Option ID for status-like fields | `f75ad846` |
| **issue state** | Issue lifecycle state | `open`, `closed` |

## Best Practices

1. **Authorize once**: Ensure `gh auth refresh -s project` has been run before project edits.
2. **Use JSON for automation**: Prefer `--format json` and `--jq` for robust scripting.
3. **Start broad, then filter**: First inspect raw item/field JSON, then apply tight filters.
4. **Treat IDs as authoritative**: Use `project id`, `item id`, `field id`, and option IDs from CLI output when editing fields.
5. **Use issue-PR linking keywords**: Add `Closes #<issue>` (or `Fixes/Resolves`) to automate closure and improve traceability.
