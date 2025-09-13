#!/bin/bash

# cc-notifier-cleanup.sh - Claude Code Session Cleanup
# Removes session-specific window data file when session ends

set +e

# Read and parse JSON input to get session_id
if [[ ! -t 0 ]]; then
    HOOK_DATA=$(cat)
    SESSION_ID=$(echo "$HOOK_DATA" | jq -r '.session_id' 2>/dev/null)
else
    SESSION_ID="interactive"
fi

# Create session-specific file path
    SESSION_DIR="/tmp/claude_window_session"
SESSION_FILE="$SESSION_DIR/$SESSION_ID"

# Validate session_id was parsed
[[ -n "$SESSION_ID" ]] || exit 0

# Remove current session file if it exists (graceful if missing)
[[ -f "$SESSION_FILE" ]] && rm "$SESSION_FILE"

# Age-based cleanup: remove files older than 5 days to prevent accumulation
if [[ -d "$SESSION_DIR" ]]; then
    # Find and delete files older than 5 days (handles orphaned session files)
    find "$SESSION_DIR" -type f -mtime +5 -delete 2>/dev/null
fi

exit 0
