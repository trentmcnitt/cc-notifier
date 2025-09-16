# cc-notifier 🔔

**Intelligent macOS notifications for Claude Code that bring you back with a single click**

Smart, context-aware notifications that know when you switch away and gently bring you back when Claude Code completes tasks. Never miss a completion again! 🚀

## ✨ What Makes cc-notifier Special

- **📱 Click-to-Focus Magic** - Click the notification to instantly return to your original window across macOS Spaces
- **🧠 Intelligent Detection** - Only notifies when you actually switch away (no spam when you're already focused)
- **🪟 Cross-Space Window Focusing** - Works seamlessly across multiple macOS Spaces using Hammerspoon
- **📝 Session-Smart** - Tracks each Claude Code session to avoid notification conflicts
- **🔧 Zero Configuration** - Works out of the box with intelligent defaults
- **⚡ Lightning Fast** - Minimal overhead, maximum responsiveness


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
After installation, the installer will provide the exact JSON configuration to add to your Claude Code settings at `~/.claude/settings.json`. The configuration will look like this:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "/Users/<your username>/.claude-code-notifier/cc-notifier-init.sh"
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
            "command": "/Users/<your username>/.claude-code-notifier/cc-notifier-notify.sh"
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
            "command": "/Users/<your username>/.claude-code-notifier/cc-notifier-notify.sh"
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
            "command": "/Users/<your username>/.claude-code-notifier/cc-notifier-cleanup.sh"
          }
        ]
      }
    ]
  }
}
```

**Important**: Copy the exact configuration from the installer output, as it will contain the correct paths for your system.

## 🏗️ How It Works

### Core Components

1. **`cc-notifier-init.sh` **- The Session Tracker**
   - Captures current window ID when Claude Code starts
   - Stores session info as a temporary file for later focus restoration

2. **`cc-notifier-notify.sh` **- The Smart Notifier**
   - Only triggers if you switched away from original window
   - Delivers elegant macOS notifications with click-to-focus action

3. **`cc-notifier-cleanup.sh` **- The Cleanup Crew**
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
# Enable debug mode
export CCN_DEBUG=1

# Check debug logs
tail -f /tmp/claude_window_session/cc-notifier.log
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

```
cc-notifier/
├── src/                    # Core hook scripts
│   ├── cc-notifier-init.sh     # SessionStart hook
│   ├── cc-notifier-notify.sh   # Stop/Notification hooks
│   ├── cc-notifier-cleanup.sh  # SessionEnd hook
│   └── lib.sh                  # Shared utilities
├── install.sh             # Installation wizard
├── uninstall.sh           # Clean removal
└── Makefile              # Development tasks
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