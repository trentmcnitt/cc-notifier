# cc_notifier.py Reference

Associated with: `cc_notifier.py` and `cc-notifier` bash wrapper

Primarily a high-level architectural reference, not a detailed implementation guide. It should be kept in sync with the actual codebase.

## Overview
`cc_notifier.py` is meant to be run as a background process via the `cc-notifier` bash wrapper, which in turn is called by Claude Code hooks. It provides intelligent notifications for both local macOS (desktop mode) and remote SSH (remote mode) environments.

**Desktop Mode**: macOS notifications with click-to-focus and optional push notifications
**Remote Mode**: Push notifications only (auto-detected via SSH environment variables)

## Key Components

- **Session Files**: `/tmp/cc_notifier/{session_id}` containing window ID, app path, and timestamp
- **Window Management**: Hammerspoon CLI for cross-space window focusing
- **Local Notifications**: terminal-notifier with `-execute` parameter for click actions
- **Push Notifications**: Pushover API integration

## Core Functions

Flows are in the order they are executed, and are performed synchronously, unless otherwise noted.

### `cc-notifier init`
**Trigger**: Claude Code SessionStart hook (Runs when Claude Code starts a new session or resumes an existing session)
**Purpose**: Capture the currently focused window ID (desktop) or save placeholder (remote)
**Flow**:
1. Parse session data from stdin JSON
2. **Desktop Mode**: Get focused window ID via Hammerspoon CLI (`hs.window.focusedWindow()`)
   **Remote Mode**: Use placeholder "REMOTE" (auto-detected via SSH environment variables)
3. Save window ID, app path, and timestamp to `/tmp/cc_notifier/{session_id}`
4. Exit immediately

### `cc-notifier notify`
**Trigger**: Claude Code Stop/Notification hooks (Stop: Runs when the main Claude Code agent has finished responding. Notification: Runs when Claude needs user attention - permission prompts, idle timeouts, auth events, and other notification types)
**Purpose**: Send intelligent notifications based on environment (local macOS or remote SSH/tmux)
**Flow**:
1. Parse hook data from stdin JSON
2. Load original window ID from session file
3. Check deduplication threshold (prevent spam within 2 seconds)
4. **Desktop Mode Only**:
   - Get current focused window ID via Hammerspoon CLI
   - Compare original vs current window ID
     - Same window: Don't send local notification, continue to push check
     - Different window: Send local notification via terminal-notifier with click-to-focus
   - Update session timestamp
5. **Remote Mode Only**: Skip local notifications entirely
6. **Push Notifications** (if push credentials exist):
   - Check idle status using ioreg (desktop) or TTY st_atime (remote)
   - Progressive interval checks: desktop [3s, 20s], remote [4s]
   - At each check: if idle time < elapsed time, user was active during check period
   - Exit early if user becomes active
   - Send push via Pushover if idle through all checks
7. Exit

### `cc-notifier cleanup`
**Trigger**: Claude Code SessionEnd hook (Runs when a Claude Code session ends, which can be due to user logout, session clear, or exiting Claude Code while prompt input is visible–i.e. via Ctrl+C)
**Purpose**: Clean up session files after Claude Code session ends
**Flow**:
1. Parse session data from stdin JSON
2. ~~Remove file associated with session ID~~ (currently disabled due to Claude Code bug #7911)
3. Perform age-based cleanup of old session files (>5 days old)
4. Exit

### `cc-notifier --version` / `cc-notifier -v`
**Purpose**: Display current version (0.3.0)
**Flow**: Print version string and exit

### Debug Mode
**Usage**: Add `--debug` flag to any command (e.g., `cc-notifier --debug notify`)
**Behavior**:
- Enables debug logging to file (not console)
- Debugging is indicated in the local and push notifications, so that users don't forget they have debugging enabled

## Notes

**Hook Data Structure**

All cc-notifier commands receive JSON data via stdin from Claude Code hooks. HookData parses and filters to these fields:
```json
{
  "session_id": "string",       // Required, always present
  "cwd": "string",              // Current working directory (default: "")
  "hook_event_name": "string",  // Event type (default: "Stop")
  "message": "string"           // Notification message, e.g. permission prompts (default: "")
}
```
Note: Claude Code sends additional fields (e.g., `transcript_path`) that are filtered out by HookData.

**Session Files**
- Stored in `/tmp/cc_notifier/`
- Named by session ID (e.g., `/tmp/cc_notifier/abc123`)
- Format (replace <> with actual values):
  ```
  <window_id>
  <app_path>
  <unix_timestamp>
  ```

**Log Files**
- Stored in `~/.cc-notifier/cc-notifier.log`
- Auto-trim

## References
- [Claude Code hooks documentation](https://docs.claude.com/en/docs/claude-code/hooks) - Complete hook behavior and data structure reference