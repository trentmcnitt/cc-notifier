#!/bin/bash

# session_start_hook.sh - Claude Code SessionStart Hook
# Captures currently focused window ID and saves to session-specific file

set +e

HAMMERSPOON_CLI="/Applications/Hammerspoon.app/Contents/Frameworks/hs/hs"

# Read and parse JSON input to get session_id
if [[ ! -t 0 ]]; then
    HOOK_DATA=$(cat)
    SESSION_ID=$(echo "$HOOK_DATA" | jq -r '.session_id' 2>/dev/null)
else
    SESSION_ID="interactive"
fi

# Create session-specific directory and file
SESSION_DIR="/tmp/claude_window_session"
SESSION_FILE="$SESSION_DIR/$SESSION_ID"

# Validate prerequisites
[[ -f "$HAMMERSPOON_CLI" && -n "$SESSION_ID" ]] || exit 1

# Create session directory if it doesn't exist
mkdir -p "$SESSION_DIR"

# Capture window ID
WINDOW_ID=$("$HAMMERSPOON_CLI" -c "local w=hs.window.focusedWindow(); print(w and w:id() or 'ERROR')" 2>/dev/null)

# Save to session file if successful
[[ "$WINDOW_ID" != "ERROR" ]] && echo "WINDOW_ID=$WINDOW_ID" >"$SESSION_FILE" || exit 1
