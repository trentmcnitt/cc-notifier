#!/bin/bash
# lib.sh - CC-Notifier Shared Debug Logging

# Configuration
LOG_FILE="/tmp/claude_window_session/cc-notifier.log"

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