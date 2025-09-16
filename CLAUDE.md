# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

cc-notifier is a macOS notification system for Claude Code hooks. It provides intelligent notifications when Claude Code completes tasks, with click-to-focus functionality that returns users to their original window across macOS Spaces.

## Development Commands

- `make lint` - Lint shell scripts with shellcheck (severity=info, all checks enabled)
- `make check` - Run all quality checks 
- `make clean` - Clean up temporary files

## Architecture

The system consists of three hook scripts that integrate with Claude Code's hook system:

- **cc-notifier-init.sh** - SessionStart hook: Captures focused window ID using Hammerspoon
- **cc-notifier-notify.sh** - Stop/Notification hooks: Sends notifications if user switched away, includes click-to-focus
- **cc-notifier-cleanup.sh** - SessionEnd hook: Cleans up session files

### Key Components

- **Session tracking**: Window IDs stored in `/tmp/claude_window_session/{session_id}`
- **Window management**: Uses Hammerspoon CLI for cross-space window focusing via `hs.window.filter`
- **Notifications**: terminal-notifier with `-execute` parameter for click-to-focus functionality
- **Intelligence**: Only notifies if user actually switched away from original window

## Dependencies

- **Hammerspoon** - Required for window focusing across macOS Spaces
- **terminal-notifier** - Required for macOS notifications with click actions
- **jq** - Required for parsing JSON hook data from Claude Code

## Debug Mode

Enable debug logging:
```bash
export CCN_DEBUG=1
```

Debug logs written to `/tmp/claude_window_session/cc-notifier.log`

## Hammerspoon Troubleshooting

### Essential Debugging Commands

```bash
# Reload Hammerspoon configuration
hs -c "hs.reload()"

# Clear Hammerspoon console for clean testing
hs -c "hs.console.clearConsole()"

# View recent console logs with timestamps
hs -c "
local console = hs.console.getConsole()
local lines = {}
for line in console:gmatch('[^\\n]+') do
    table.insert(lines, line)
end
for i = math.max(1, #lines-10), #lines do
    print(lines[i])
end"

### Debugging Workflow

1. **Clear console**: `hs -c "hs.console.clearConsole()"`
2. **Test operation**: Run cc-notifier or test command
3. **Check console**: View logs with timestamps to correlate errors
4. **Reload if needed**: `hs -c "hs.reload()"` if Hammerspoon gets stuck

Use alongside `CCN_DEBUG=1` to get detailed logs in `/tmp/claude_window_session/cc-notifier.log`

Check out [Hammerspoon docs](https://www.hammerspoon.org/docs/) for more commands and troubleshooting tips, like [hs.logger](https://www.hammerspoon.org/docs/hs.logger.html)

## Installation

Run `./install.sh` to set up dependencies and generate Claude Code hook configuration. The installer provides JSON configuration to add to `~/.claude/settings.json`.