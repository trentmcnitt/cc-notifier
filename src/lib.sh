#!/bin/bash
# lib.sh - CC-Notifier Shared Utilities

# Path constants
SESSION_DIR="/tmp/claude_code_notifier"
# shellcheck disable=SC2034  # Used by sourcing scripts
HAMMERSPOON_CLI="/Applications/Hammerspoon.app/Contents/Frameworks/hs/hs"
# shellcheck disable=SC2034  # Used by sourcing scripts
TERMINAL_NOTIFIER="/opt/homebrew/bin/terminal-notifier"

# Configuration
LOG_FILE="$SESSION_DIR/cc-notifier.log"

# Debug flag from environment (CCN_DEBUG=1 to enable)
CCN_DEBUG=${CCN_DEBUG:-0}

# Debug logging function
debug_log() {
    if [[ "$CCN_DEBUG" == "1" ]]; then
        local timestamp
        timestamp=$(date '+%H:%M:%S')
        echo "$timestamp [$$] $*" >> "$LOG_FILE"
    fi
}