#!/bin/bash

# cc-notifier-cleanup.sh - Claude Code Notifier Cleanup
# Removes session-specific files and performs general cleanup of old session files

# shellcheck source=src/lib.sh
source "$(dirname "$0")/lib.sh"

set +e

debug_log "CLEANUP: Starting session cleanup"

# Read and parse JSON input to get session_id
if [[ ! -t 0 ]]; then
    HOOK_DATA=$(cat)
    SESSION_ID=$(echo "$HOOK_DATA" | jq -r '.session_id' 2>/dev/null)
else
    SESSION_ID="interactive"
fi

# Create session-specific file path
SESSION_FILE="$SESSION_DIR/$SESSION_ID"

# Validate session_id was parsed
[[ -n "$SESSION_ID" ]] || exit 0

# Remove current session file if it exists (graceful if missing)
if [[ -f "$SESSION_FILE" ]]; then
    rm "$SESSION_FILE"
    debug_log "CLEANUP: Removed session file for $SESSION_ID"
else
    debug_log "CLEANUP: Session file for $SESSION_ID not found (may have already been cleaned)"
fi

# Age-based cleanup: remove files older than 5 days to prevent accumulation
if [[ -d "$SESSION_DIR" ]]; then
    # Find and delete files older than 5 days (handles orphaned session files)
    AGED_FILES_LIST=$(find "$SESSION_DIR" -type f -mtime +5 2>/dev/null)
    AGED_FILES_COUNT=$(echo "$AGED_FILES_LIST" | wc -l)
    find "$SESSION_DIR" -type f -mtime +5 -delete 2>/dev/null
    debug_log "CLEANUP: Age cleanup processed $AGED_FILES_COUNT old files"
fi

exit 0
