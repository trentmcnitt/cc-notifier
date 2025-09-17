# cc-notifier 🔔

**Intelligent macOS notifications for Claude Code that bring you back to your original window with a single click**

Smart, context-aware notifications that know when you switch away and gently bring you back when Claude Code completes tasks or needs input from you.

## ✨ What Makes cc-notifier Special

- **📱 Click-to-Focus Magic** - Click the notification to instantly return to your original window across macOS Spaces
- **🧠 Intelligent Detection** - Only notifies when you actually switch away (no spam when you're already focused)
- **🪟 Cross-Space Window Focusing** - Works seamlessly across multiple macOS Spaces using Hammerspoon
- **📝 Session-Smart** - Tracks each Claude Code session to avoid notification conflicts
- **🔧 Zero Configuration** - Works out of the box with intelligent defaults
- **⚡ Lightning Fast** - Minimal overhead, maximum responsiveness

Most notification systems only take you to the app, not the exact window you were working in, which isn't ideal when you have multiple IDE or terminal windows open.
- cc-notifier solves this by tracking the exact window you were using and restoring focus to it, even if it's in a different Space.

## ⚙️ Installation

### Quick Install (Recommended)
```bash
# Clone the repository
git clone https://github.com/your-username/cc-notifier.git
cd cc-notifier

# Run the installer
./install.sh
```

### 🔧 Hammerspoon Setup
**Important**: After installing Hammerspoon, ensure these modules are loaded in your `~/.hammerspoon/init.lua`:

```lua
require("hs.ipc")
require("hs.window")
require("hs.window.filter")
require("hs.timer")
```

After adding these modules, reload Hammerspoon:
```bash
# Reload Hammerspoon configuration (can also use the Hammerspoon GUI)
hs -c "hs.reload()"
```

These modules are essential for cc-notifier's cross-space window focusing functionality.

### ⚡ Quick Start
After installation, the installer will provide the exact JSON configuration to add to your Claude Code settings at `~/.claude/settings.json`. If `~/.local/bin` is in your PATH, the configuration will look like this (using simple commands):

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "cc-notifier init"
          }
        ]
      }
    ],
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "cc-notifier notify"
          }
        ]
      }
    ],
    "Notification": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "cc-notifier notify"
          }
        ]
      }
    ],
    "SessionEnd": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "cc-notifier cleanup"
          }
        ]
      }
    ]
  }
}
```

## 🏗️ How It Works

### Core Components

1. **`cc-notifier init`** - The Session Tracker
   - Captures current window ID when Claude Code starts
   - Stores session info as a temporary file for later focus restoration

2. **`cc-notifier notify`** - The Smart Notifier
   - Only triggers if you switched away from original window
   - Delivers elegant macOS notifications with click-to-focus action

3. **`cc-notifier cleanup`** - The Cleanup Crew
   - Removes session files after completion
   - Keeps your system tidy

## 🛠️ Requirements

### Required Dependencies
- **macOS** - Any recent version
- **Hammerspoon** - For cross-space window focusing
  ```bash
  brew install --cask hammerspoon
  ```
- **terminal-notifier** - For macOS notifications
  ```bash
  brew install terminal-notifier
  ```
- **jq** - For JSON parsing
  ```bash
  brew install jq
  ```

### Optional Development Tools
- **shellcheck** - For linting (development)
  ```bash
  brew install shellcheck
  ```

## 💡 Troubleshooting

### Wrong Window Being Focused
**Problem**: Notifications take you to the wrong window instead of where Claude Code was originally running.

**Cause**: The window ID is captured when Claude Code starts a session. A "session" starts when:
- Claude Code launches for the first time
- You clear or resume a session

If you start/resume Claude Code in one window then immediately switch to another window, it captures the wrong window ID.

**Solution**:
- Restart Claude Code, OR
- Clear and resume your session (Cmd+Shift+P → "Claude Code: Clear and Resume Session")

**Prevention**: Make sure Claude Code is focused in your intended work window when starting or resuming a session.

## 🔍 Debugging

### Hammerspoon Window Discovery

**For most users, this is automatic** - Hammerspoon tracks windows as you use them normally. However, if you restart or reload Hammerspoon, you may need to help it "discover" windows:

- **Quick fix**: Visit each Space (or at least a few) and click on a few windows before expecting cross-space focus to work
- **Why**: Hammerspoon's `setCurrentSpace(false)` filter can only find windows in Spaces you've already visited
- **When this matters**: Only after restarting/reloading Hammerspoon (e.g., during debugging)
- **Normal usage**: Since Hammerspoon is usually set to launch at login and runs continuously, regular workflow naturally populates its window cache

This is rarely an issue in practice - if you use multiple Spaces, you'll naturally visit them during normal work, allowing Hammerspoon to track all windows automatically. But when debugging or testing, just remember it can act funny until you've visited a few spaces and clicked on some windows.

### Debug Logging

Enable detailed logging to troubleshoot issues:

```bash
# In the Claude Code settings.json, call the hook you want to debug with like this:
`CCN_DEBUG=1 cc-notifier <command>`

# Check debug logs
tail -f /tmp/claude_code_notifier/cc-notifier.log
```

Debug logs show:
- Window ID capture and focus detection
- Session management details
- Notification triggering logic
- Focus restoration attempts

## 🧪 Development & Testing

### Quality Checks
```bash
# Run linting
make lint

# Run all checks
make check

# Clean temporary files
make clean
```

### Architecture Overview

For technical background on key challenges and discoveries, see [`docs/RESEARCH_LOG.md`](docs/RESEARCH_LOG.md). The document covers technical problems that had to be solved for cross-space window focusing on macOS.

### Development Structure
```
cc-notifier/
├── src/                    # Core hook scripts
│   ├── cc-notifier             # Main command dispatcher
│   ├── cc-notifier-init.sh     # SessionStart hook (called by cc-notifier init)
│   ├── cc-notifier-notify.sh   # Stop/Notification hooks (called by cc-notifier notify)
│   ├── cc-notifier-cleanup.sh  # SessionEnd hook (called by cc-notifier cleanup)
│   └── lib.sh                  # Shared utilities
├── install.sh             # Installation wizard
├── uninstall.sh           # Clean removal
└── Makefile              # Development tasks
```

### Installation Structure
After running `./install.sh`, files are installed to standard Unix locations:
```
~/.local/
├── bin/
│   └── cc-notifier         # Main command (in PATH if ~/.local/bin is in PATH)
└── share/
    └── cc-notifier/        # Support files
        ├── lib.sh
        ├── cc-notifier-init.sh
        ├── cc-notifier-notify.sh
        └── cc-notifier-cleanup.sh
```

## 🌟 Why cc-notifier?

Unlike simple notification systems, cc-notifier:
  - **Understands context** - Won't notify when you're already focused
  - **Restores precisely** - Returns to exact window (useful when multiple windows for the same app are open), even across Spaces
  - **Handles complexity** - Works with any number of simultaneous sessions
  - **Maintains focus** - Minimal disruption to your workflow

## 🤝 Contributing

We welcome contributions! Please:

1. **Fork & Branch**: Create a descriptive branch name
2. **Lint First**: Run `make lint` before committing
3. **Test Thoroughly**: Verify installation and functionality
4. **Document Changes**: Update docs for new features

## 📝 License

MIT License - Feel free to use, modify, and distribute