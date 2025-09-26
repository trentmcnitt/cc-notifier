# cc_notifier.py Reference

Associated with: `cc-notifier.py` and `cc-notifier` bash wrapper

Primarily a high-level architectural reference, not a detailed implementation guide. It should be kept in sync with the actual codebase.

## Overview
`cc-notifier.py` is meant to be run as a background process via the `cc-notifier` bash wrapper, which in turn is called by Claude Code hooks. It contains the code to provide intelligent macOS notifications with click-to-focus functionality, and push notifications if the user is away from their computer.

## Key Components

- **Session Files**: `/tmp/cc_notifier/{session_id}` containing window ID and timestamp
- **Window Management**: Hammerspoon CLI for cross-space window focusing
- **Local Notifications**: terminal-notifier with `-execute` parameter for click actions
- **Push Notifications**: Pushover API integration

## Core Functions

Flows are in the order they are executed, and are performed synchronously, unless otherwise noted.

### `cc-notifier init`
**Trigger**: Claude Code SessionStart hook (Runs when Claude Code starts a new session or resumes an existing session)
**Purpose**: Capture the currently focused window ID when Claude Code starts a session
**Flow**:
1. Parse session data from stdin JSON
2. Get focused window ID via Hammerspoon CLI (`hs.window.focusedWindow()`)
3. Save window ID + timestamp to `/tmp/cc_notifier/{session_id}`
4. Exit immediately

### `cc-notifier notify`
**Trigger**: Claude Code Stop/Notification hooks (Stop: Runs when the main Claude Code agent has finished responding. Notification: Runs when Claude needs to notify the user, which is either when it needs permission to use a tool, or when the prompt has been idle for 60 seconds)
**Purpose**: Send intelligent local notifications when user switched away from original window and check if user is away from computer for push notifications
**Flow**:
1. Parse hook data from stdin JSON
2. Load original window ID from session file
3. Check deduplication threshold (prevent spam within X seconds)
4. Get current focused window ID via Hammerspoon CLI
5. Compare original vs current window ID
  - Same window (user is not focused on another app): Don't send local notification, but continue to push check
  - Different window (user is focused on another app):
    1. Send local notification immediately via terminal-notifier with click-to-focus
    2. Update session timestamp
6. If push credentials exist, check user idle status at progressive intervals
    - If user becomes active at any check: exit early, no push notification
    - If user stays idle through all checks: send push notification via Pushover API
7. Exit

### `cc-notifier cleanup`
**Trigger**: Claude Code SessionEnd hook (Runs when a Claude Code session ends, which can be due to user logout, session clear, or exiting Claude Code while prompt input is visible–i.e. via Ctrl+C)
**Purpose**: Clean up session files after Claude Code session ends
**Flow**:
1. Parse session data from stdin JSON
2. ~~Remove file associated with session id~~ (currently disabled due to Claude Code bug #7911)
3. Perform age-based cleanup of old session files (>X days old)
4. Exit

### `cc-notifier --version` / `cc-notifier -v`
**Purpose**: Display current version (0.2.0)
**Flow**: Print version string and exit

### Debug Mode
**Usage**: Add `--debug` flag to any command (e.g., `cc-notifier --debug notify`)
**Behavior**:
- Enables debug logging to file (not console)
- Debugging is indicated in the local and push notifications, so that users don't forget they have debugging enabled

## Notes

**Hook Data Structure**

All cc-notifier commands receive JSON data via stdin from Claude Code hooks containing:
```json
{
  // Common fields (always present)
  "session_id": "string",
  "transcript_path": "string",  // Path to conversation JSON
  "cwd": "string",              // Current working directory when hook is invoked

  // Event-specific fields
  "hook_event_name": "string",
  // ... additional fields depending on hook type
}
```

**Session Files**
- Stored in `/tmp/cc_notifier/`
- Named by session ID (e.g., `/tmp/cc_notifier/abc123`)
- Format (replace <> with actual values):
  ```
  <window_id>
  <unix_timestamp>
  ```

**Log Files**
- Stored in `~/.cc-notifier/cc-notifier.log`
- Auto-trim

## References
- [Claude Code hooks documentation](https://docs.claude.com/en/docs/claude-code/hooks) - Complete hook behavior and data structure reference