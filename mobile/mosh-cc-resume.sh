#!/bin/bash
# Resume Claude Code session from push notification
#
# PURPOSE:
# This script is designed to be called from a Blink Shell URL scheme when you tap
# a push notification from cc-notifier. It automatically reconnects to your remote
# server via mosh and resumes your exact Claude Code session.
#
# WORKFLOW:
# 1. cc-notifier sends push notification with custom URL
# 2. You tap notification on your phone
# 3. Pushover app shows the URL link
# 4. Tapping the link opens Blink Shell via URL scheme
# 5. Blink Shell executes this script with session_id and working_dir
# 6. Script resumes your Claude Code session in tmux
# 7. You're back in your exact conversation!
#
# USAGE: mosh-cc-resume.sh <session_id> <working_directory>
#
# CUSTOMIZATION POINTS:
# - SESSION_NAME: Change to your preferred tmux session name
# - NOTIFY_WINDOW: Window number for notifications (prevents accumulation)
# - Paths: Adjust ~/bin/ and keychain paths for your system
#
# WORKAROUND for Claude Code API key issue with mosh/SSH:
# The --dangerously-skip-permissions flag bypasses permission prompts that would
# block automated session resumption. This is safe in this context because:
# - You've already granted permissions in the original session
# - The session is being resumed, not started fresh
# - You're the same authenticated user
#
# Related GitHub Issues:
# - https://github.com/anthropics/claude-code/issues/5515 (API key persistence)
# - https://github.com/anthropics/claude-code/issues/642 (mosh support)
# - https://github.com/anthropics/claude-code/issues/5957 (SSH support)
# - https://github.com/anthropics/claude-code/issues/9403 (OAuth persistence)

# Ensure cleanup daemon is running (optional but recommended)
# This prevents orphaned tmux sessions from accumulating
pgrep -f "tmux-idle-cleanup.sh" > /dev/null || nohup ~/bin/tmux-idle-cleanup.sh > /dev/null 2>&1 &

SESSION_ID="$1"
WORKING_DIR="$2"
SESSION_NAME="claude_code_resume"  # CUSTOMIZE: Your preferred tmux session name
NOTIFY_WINDOW=9                    # CUSTOMIZE: Window number for notifications

if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    # Session exists - use dedicated window 9 for notifications
    # This prevents notification windows from accumulating (smart!)
    tmux kill-window -t "$SESSION_NAME:$NOTIFY_WINDOW" 2>/dev/null || true
    tmux new-window -t "$SESSION_NAME:$NOTIFY_WINDOW" -c "$WORKING_DIR" "claude --resume $SESSION_ID --dangerously-skip-permissions"
    tmux attach -t "$SESSION_NAME"
else
    # Create new session with keychain unlock if needed
    # Note: Use show-keychain-info (not dump-keychain) for reliable lock detection
    # CUSTOMIZE: Adjust keychain path if yours differs
    tmux new-session -s "$SESSION_NAME" -c "$WORKING_DIR" "if ! security show-keychain-info ~/Library/Keychains/login.keychain-db 2>/dev/null; then echo '🔓 Unlocking keychain for Claude Code...'; security unlock-keychain ~/Library/Keychains/login.keychain-db; fi && claude --resume $SESSION_ID --dangerously-skip-permissions"
fi
