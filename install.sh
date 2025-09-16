#!/bin/bash

# Claude Code Notifier Installer
# Installs notification hooks for Claude Code on macOS

set -e

# Installation directories
BIN_DIR="$HOME/.local/bin"
SHARE_DIR="$HOME/.local/share/cc-notifier"
CLAUDE_SETTINGS="$HOME/.claude/settings.json"

echo "🚀 Installing Claude Code Notifier..."
echo "📁 Command location: $BIN_DIR"
echo "📁 Support files: $SHARE_DIR"

# Check dependencies
echo "📋 Checking dependencies..."

# Check Hammerspoon CLI
HAMMERSPOON_CLI="/Applications/Hammerspoon.app/Contents/Frameworks/hs/hs"
if [[ ! -f "$HAMMERSPOON_CLI" ]]; then
    echo "❌ Hammerspoon CLI not found at $HAMMERSPOON_CLI"
    echo "   Please install Hammerspoon from https://www.hammerspoon.org/ then install the Hammerspoon CLI using \"hs.ipc.cliInstall()\" from the Hammerspoon console."
    exit 1
fi

# Check jq
if ! command -v jq &>/dev/null; then
    echo "❌ jq is required but not installed. Installing..."
    if command -v brew &>/dev/null; then
        brew install jq
    else
        echo "❌ Homebrew not found. Please install jq manually: https://stedolan.github.io/jq/"
        exit 1
    fi
fi

# Check terminal-notifier
if ! command -v terminal-notifier &>/dev/null; then
    echo "❌ terminal-notifier is required but not installed. Installing..."
    if command -v brew &>/dev/null; then
        brew install terminal-notifier
    else
        echo "❌ Homebrew not found. Please install terminal-notifier manually"
        exit 1
    fi
fi

echo "✅ Dependencies check complete"

# Create installation directories
echo "🔧 Setting up installation directories..."
mkdir -p "$BIN_DIR"
mkdir -p "$SHARE_DIR"

# Get the directory where this install script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Copy main command to bin directory
echo "📋 Installing command dispatcher..."
cp "$SCRIPT_DIR/src/cc-notifier" "$BIN_DIR/"
chmod +x "$BIN_DIR/cc-notifier"

# Copy support scripts to share directory
echo "📋 Installing support scripts..."
cp "$SCRIPT_DIR/src/lib.sh" "$SHARE_DIR/"
cp "$SCRIPT_DIR/src/cc-notifier-init.sh" "$SHARE_DIR/"
cp "$SCRIPT_DIR/src/cc-notifier-cleanup.sh" "$SHARE_DIR/"
cp "$SCRIPT_DIR/src/cc-notifier-notify.sh" "$SHARE_DIR/"

# Make support scripts executable
chmod +x "$SHARE_DIR"/*.sh
echo "✅ Scripts installation complete"

# Test notification permissions
echo "🔔 Testing notification permissions..."
terminal-notifier -message "Claude Code Notifier is ready!" -title "Setup Complete" -sound "Funk"

# Check PATH and determine command format
echo ""
echo "🔍 Checking PATH configuration..."
if printf '%s\n' "${PATH//:/$'\n'}" | grep -Fxq "$HOME/.local/bin"; then
    echo "✅ ~/.local/bin is in your PATH"
    COMMAND_PREFIX="cc-notifier"
    PATH_STATUS="in-path"
else
    echo "⚠️  ~/.local/bin is not in your PATH"
    echo "   Commands will use full paths"
    COMMAND_PREFIX="$BIN_DIR/cc-notifier"
    PATH_STATUS="not-in-path"
fi

# Check if Claude settings file exists
if [[ ! -f "$CLAUDE_SETTINGS" ]]; then
    echo "📁 Creating Claude settings directory..."
    mkdir -p "$(dirname "$CLAUDE_SETTINGS")"
fi

# Generate hook configuration using jq for clean, validated JSON
echo "⚙️  Generating hook configuration..."

# Create hook configuration with jq (ensures valid JSON)
HOOK_CONFIG=$(jq -n \
  --arg session_start "$COMMAND_PREFIX init" \
  --arg stop "$COMMAND_PREFIX notify" \
  --arg session_end "$COMMAND_PREFIX cleanup" \
  '{
    "hooks": {
      "SessionStart": [{"matcher": "", "hooks": [{"type": "command", "command": $session_start}]}],
      "Stop": [{"matcher": "", "hooks": [{"type": "command", "command": $stop}]}],
      "Notification": [{"matcher": "", "hooks": [{"type": "command", "command": $stop}]}],
      "SessionEnd": [{"matcher": "", "hooks": [{"type": "command", "command": $session_end}]}]
    }
  }')

echo ""
echo "📋 Add this to your ~/.claude/settings.json:"
echo ""
echo "$HOOK_CONFIG"
echo ""
echo "   Note: If you already have a 'hooks' section, merge the hook types accordingly."

echo ""
echo "🔧 Required Hammerspoon Configuration:"
echo ""
echo "Add these lines to your ~/.hammerspoon/init.lua file:"
echo ""
echo 'require("hs.ipc")'
echo 'require("hs.window")'
echo 'require("hs.window.filter")'
echo 'require("hs.timer")'
echo ""
echo "After adding these modules:"
echo "1. Save the file"
echo "2. Reload Hammerspoon config: hs -c \"hs.reload()\" (or use the Hammerspoon GUI)"
echo "3. Or restart Hammerspoon.app"

# Provide PATH setup guidance if needed
if [[ "$PATH_STATUS" == "not-in-path" ]]; then
    echo ""
    echo "💡 Optional: Add ~/.local/bin to your PATH for cleaner commands"
    echo ""
    echo "Add this line to your shell profile (~/.bashrc, ~/.zshrc, etc.):"
    echo "export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo ""
    echo "Then restart your terminal or run: source ~/.zshrc"
    echo "This will allow you to use 'cc-notifier' instead of full paths."
    echo ""
fi

echo ""
echo "🎉 Installation complete!"
echo ""
echo "📖 How it works:"
echo "1. When you start a Claude Code session, it captures your current window"
echo "2. When Claude finishes and you've switched to another app, you get a notification"
echo "3. Click the notification to return to your original window"
echo "4. If you're still on the original window, no notification is sent"
echo ""
echo "📁 Command: $BIN_DIR/cc-notifier"
echo "📁 Support files: $SHARE_DIR"
echo "⚙️  Configuration: ~/.claude/settings.json"
echo ""
echo "Happy coding! 🚀"