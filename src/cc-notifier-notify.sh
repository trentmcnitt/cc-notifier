#!/bin/bash

# cc-notifier-notify.sh - Claude Code Notifier intelligent notifications
# Detects if user switched away, sends click-to-focus notification if needed

# shellcheck source=src/lib.sh
source "$(dirname "$0")/lib.sh"

set +e

debug_log "NOTIFY: Starting notification check"

# Read and parse JSON input to get session_id and notification data
if [[ ! -t 0 ]]; then
    HOOK_DATA=$(cat)
    SESSION_ID=$(echo "$HOOK_DATA" | jq -r '.session_id' 2>/dev/null)
    CWD=$(echo "$HOOK_DATA" | jq -r '.cwd // ""' 2>/dev/null)
    HOOK_EVENT_NAME=$(echo "$HOOK_DATA" | jq -r '.hook_event_name // "Stop"' 2>/dev/null)
    HOOK_MESSAGE=$(echo "$HOOK_DATA" | jq -r '.message // ""' 2>/dev/null)
else
    SESSION_ID="interactive"
    CWD=""
    HOOK_EVENT_NAME="Stop"
    HOOK_MESSAGE=""
fi

# Create session-specific directory and file paths
SESSION_FILE="$SESSION_DIR/$SESSION_ID"

# Validate prerequisites
[[ -f "$HAMMERSPOON_CLI" ]] || error_exit "Hammerspoon CLI not found at $HAMMERSPOON_CLI"
[[ -f "$TERMINAL_NOTIFIER" ]] || error_exit "terminal-notifier not found at $TERMINAL_NOTIFIER"
[[ -n "$SESSION_ID" ]] || error_exit "SESSION_ID is empty"

# Validate session file exists
[[ -f "$SESSION_FILE" ]] || error_exit "Session file not found: $SESSION_FILE"

# Load original window ID from session file
# shellcheck source=/dev/null
source "$SESSION_FILE"

# Validate WINDOW_ID was loaded from session file
[[ -n "$WINDOW_ID" ]] || error_exit "WINDOW_ID not found in session file: $SESSION_FILE"

# Get current focused window ID
CURRENT_ID=$("$HAMMERSPOON_CLI" -c "local w=hs.window.focusedWindow(); print(w and w:id() or 'ERROR')" 2>/dev/null)

# Exit if we can't get current window ID
[[ "$CURRENT_ID" != "ERROR" && -n "$CURRENT_ID" ]] || error_exit "Failed to get current window ID from Hammerspoon"

debug_log "NOTIFY: Window comparison - Current:$CURRENT_ID Original:$WINDOW_ID"

# Check if user is still on the original window
if [[ "$WINDOW_ID" == "$CURRENT_ID" ]]; then
    debug_log "NOTIFY: User still active, no notification needed"
    exit 0
fi

debug_log "NOTIFY: User switched away, generating notification"

# Generate dynamic notification content
if [[ -n "$CWD" ]]; then
    PROJECT_NAME=$(basename "$CWD")
    NOTIFICATION_SUBTITLE="$PROJECT_NAME"
else
    NOTIFICATION_SUBTITLE="Task Completed"
fi

# Determine message based on hook type
if [[ "$HOOK_EVENT_NAME" == "Notification" && -n "$HOOK_MESSAGE" ]]; then
    NOTIFICATION_MESSAGE="$HOOK_MESSAGE"
else
    NOTIFICATION_MESSAGE="Completed task"
fi

debug_log "NOTIFY: Content - Subtitle='$NOTIFICATION_SUBTITLE' Message='$NOTIFICATION_MESSAGE' Event='$HOOK_EVENT_NAME'"

# User has switched away - send intelligent notification with click-to-focus
#
# HAMMERSPOON WINDOW FILTER WORKAROUND:
# We use a dual-filter approach instead of setCurrentSpace(nil) due to it causing
# infinite hangs and IPC port invalidation errors
#
# Issue: Issues getting windows accross macOS Spaces (https://github.com/Hammerspoon/hammerspoon/issues/3276#issuecomment-2354681473)
#
# Solution: Combine two separate filters (idea taken from https://github.com/Hammerspoon/hammerspoon/issues/3276#issuecomment-2354681473)
# 1. setCurrentSpace(true)  - Gets windows in current macOS Space
# 2. setCurrentSpace(false) - Gets windows in other macOS Spaces
# We then combine the two lists and search for our original window ID to focus it.
#
# This approach provides the same functionality as setCurrentSpace(nil) but without hanging.
HAMMERSPOON_COMMAND="$HAMMERSPOON_CLI -c \"
local current = require('hs.window.filter').new():setCurrentSpace(true):getWindows()
local other = require('hs.window.filter').new():setCurrentSpace(false):getWindows()
for _,w in pairs(other) do table.insert(current, w) end
for _,w in pairs(current) do
  if w:id()==$WINDOW_ID then
    w:focus()
    require('hs.timer').usleep(300000)
    return
  end
end\""

# Send notification with click-to-execute
"$TERMINAL_NOTIFIER" \
    -title "Claude Code 🔔" \
    -subtitle "$NOTIFICATION_SUBTITLE" \
    -message "$NOTIFICATION_MESSAGE" \
    -sound "Glass" \
    -ignoreDnD \
    -execute "$HAMMERSPOON_COMMAND" &

debug_log "NOTIFY: Notification sent with click-to-focus functionality"

# Exit immediately (don't wait for notification)
exit 0
