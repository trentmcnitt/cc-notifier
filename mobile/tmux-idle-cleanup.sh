#!/bin/bash
# Automatically kill idle tmux sessions that have been inactive for too long
#
# PURPOSE:
# When using the mobile development workflow (desktop → phone → back to desktop),
# you'll create tmux sessions that you might forget to clean up. This daemon runs
# in the background and automatically terminates sessions that have been idle for
# too long, preventing resource waste on your remote server.
#
# FEATURES:
# - Kills detached tmux sessions after IDLE_MINUTES of inactivity
# - Smart shutdown: Exits when no sessions remain or after MAX_HOURS
# - Respects attached sessions (never kills while you're using it)
# - Logs all actions to /tmp/tmux-cleanup.log
#
# AUTO-START:
# Add to your ~/.zshrc or ~/.bashrc on the remote server:
#   pgrep -f "tmux-idle-cleanup.sh" > /dev/null || nohup ~/bin/tmux-idle-cleanup.sh > /dev/null 2>&1 &
#
# CUSTOMIZATION:
# - IDLE_MINUTES: How long before killing idle sessions
# - MAX_HOURS: Maximum daemon runtime before auto-shutdown
# - Check interval: Currently 1 hour (sleep 3600)

IDLE_MINUTES=600  # Kill after 10 hours of inactivity (CUSTOMIZE as needed)
MAX_HOURS=24      # Auto-shutdown after this many hours (prevents runaway daemon)
START_TIME=$(date +%s)  # Record when we started

while true; do
    # Get current time once per check cycle
    CURRENT_TIME=$(date +%s)

    # Get all tmux sessions
    tmux list-sessions -F "#{session_name}:#{session_attached}:#{session_activity}" 2>/dev/null | while IFS=: read -r session_name attached last_activity; do
        # Skip if someone is attached to this session
        if [[ "$attached" == "1" ]]; then
            continue
        fi

        # Session is detached - check how long it's been idle
        IDLE_SECONDS=$(( CURRENT_TIME - last_activity ))
        IDLE_MIN=$(( IDLE_SECONDS / 60 ))

        if [[ $IDLE_MIN -ge $IDLE_MINUTES ]]; then
            echo "$(date): Killing session '$session_name' (idle for ${IDLE_MIN} minutes)" >> /tmp/tmux-cleanup.log
            tmux kill-session -t "$session_name"
        fi
    done

    # Shutdown if no sessions remain
    if ! tmux list-sessions 2>/dev/null; then
        echo "$(date): No tmux sessions remaining, shutting down cleanup daemon" >> /tmp/tmux-cleanup.log
        exit 0
    fi

    # Shutdown if max runtime exceeded
    ELAPSED=$(( $(date +%s) - START_TIME ))
    if [[ $ELAPSED -ge $(( MAX_HOURS * 3600 )) ]]; then
        echo "$(date): Max runtime (${MAX_HOURS} hours) reached, shutting down cleanup daemon" >> /tmp/tmux-cleanup.log
        exit 0
    fi

    # Check every hour (CUSTOMIZE: reduce for more aggressive cleanup)
    sleep 3600
done
