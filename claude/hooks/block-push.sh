#!/usr/bin/env bash
# PreToolUse hook (Bash): block commands that push to or merge on GitHub, so pushing stays a manual step.
# Matches the subcommand position after any global flags, e.g. 'git -C dir push' or 'gh -R owner/repo stack push',
# but not the word 'push' elsewhere, e.g. in a commit message.
cmd=$(jq -r '.tool_input.command // empty')

# Zero or more flags, each optionally followed by one value: -C dir, --no-pager, -R owner/repo
flags='(\s+-\S+(\s+[^-[:space:]]\S*)?)*'
start='(^|[;&|(`/[:space:]])'

if grep -qE "${start}git${flags}\s+push\b|${start}gh${flags}\s+stack${flags}\s+(push|submit|sync|merge)\b" <<<"$cmd"; then
  echo "Blocked by ~/.claude/hooks/block-push.sh: pushing and merging are done by the user. Ask them to run it with '! <command>'." >&2
  exit 2
fi
exit 0
