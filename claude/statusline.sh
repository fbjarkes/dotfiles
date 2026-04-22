#!/bin/bash
# Read JSON data that Claude Code sends to stdin
input=$(cat)

# Extract fields using jq
MODEL=$(echo "$input" | jq -r '.model.display_name')
DIR=$(echo "$input" | jq -r '.workspace.current_dir')
# The "// 0" provides a fallback if the field is null
PCT=$(echo "$input" | jq -r '.context_window.used_percentage // 0' | cut -d. -f1)

# Git status: branch + dirty indicator
GIT_INFO=""
if git -C "$DIR" rev-parse --git-dir &>/dev/null; then
  BRANCH=$(git -C "$DIR" symbolic-ref --short HEAD 2>/dev/null || git -C "$DIR" rev-parse --short HEAD 2>/dev/null)
  DIRTY=$(git -C "$DIR" status --porcelain 2>/dev/null)
  [[ -n "$DIRTY" ]] && BRANCH="${BRANCH}*"
  GIT_INFO=" | ⎇ ${BRANCH}"
fi

# Output the status line - ${DIR##*/} extracts just the folder name
echo "[$MODEL] 📁 ${DIR##*/}${GIT_INFO} | ${PCT}% context"
