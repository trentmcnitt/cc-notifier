#!/bin/bash

# stop_hook.sh - Claude Code Stop Hook with Intelligent Notifications
# Detects if user switched away, sends click-to-focus notification if needed

set +e

HAMMERSPOON_CLI="/Applications/Hammerspoon.app/Contents/Frameworks/hs/hs"
TERMINAL_NOTIFIER="/opt/homebrew/bin/terminal-notifier"

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
SESSION_DIR="/tmp/claude_window_session"
SESSION_FILE="$SESSION_DIR/$SESSION_ID"

# Validate prerequisites
[[ -f "$HAMMERSPOON_CLI" && -f "$TERMINAL_NOTIFIER" && -n "$SESSION_ID" ]] || exit 1

# Validate session file exists
[[ ! -f "$SESSION_FILE" ]] && exit 1

# Load original window ID from session file
# shellcheck source=/dev/null
source "$SESSION_FILE"

# Validate WINDOW_ID was loaded from session file
[[ -n "$WINDOW_ID" ]] || exit 1

# Get current focused window ID
CURRENT_ID=$("$HAMMERSPOON_CLI" -c "local w=hs.window.focusedWindow(); print(w and w:id() or 'ERROR')" 2>/dev/null)

# Exit if we can't get current window ID
[[ "$CURRENT_ID" == "ERROR" || -z "$CURRENT_ID" ]] && exit 1

# Check if user is still on the original window
if [[ "$WINDOW_ID" == "$CURRENT_ID" ]]; then
    # User is still active on original window - no notification needed
    exit 0
fi

# Generate dynamic notification content
# Extract parent/project name from cwd for subtitle
if [[ -n "$CWD" ]]; then
    PROJECT_NAME=$(basename "$CWD")
    PARENT_NAME=$(basename "$(dirname "$CWD")")
    NOTIFICATION_SUBTITLE="$PARENT_NAME/$PROJECT_NAME"
else
    NOTIFICATION_SUBTITLE="Task Completed"
fi

# Determine message based on hook type
if [[ "$HOOK_EVENT_NAME" == "Notification" && -n "$HOOK_MESSAGE" ]]; then
    NOTIFICATION_MESSAGE="$HOOK_MESSAGE"
else
    NOTIFICATION_MESSAGE="Completed task"
fi

# User has switched away - send intelligent notification with click-to-focus
HAMMERSPOON_COMMAND="$HAMMERSPOON_CLI -c \"
local wf=require('hs.window.filter').new():setCurrentSpace(nil)
for _,w in pairs(wf:getWindows()) do
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

# Exit immediately (don't wait for notification)
exit 0
