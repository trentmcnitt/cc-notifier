#!/bin/bash

# cc-notifier-init.sh - Claude Code Notifier Initialization
# Captures currently focused window ID and saves to session-specific file

# shellcheck source=src/lib.sh
source "$(dirname "$0")/lib.sh"

set +e

HAMMERSPOON_CLI="/Applications/Hammerspoon.app/Contents/Frameworks/hs/hs"

debug_log "INIT: Starting session initialization"

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

debug_log "INIT: Window captured ID=$WINDOW_ID for session $SESSION_ID"

# Save to session file if successful
if [[ "$WINDOW_ID" != "ERROR" ]]; then
    echo "WINDOW_ID=$WINDOW_ID" >"$SESSION_FILE"
    debug_log "INIT: Session file created successfully at $SESSION_FILE"
else
    debug_log "INIT: Failed to capture window ID"
    exit 1
fi
