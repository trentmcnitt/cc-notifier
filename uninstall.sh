#!/bin/bash
set -e

echo "🗑️  Uninstalling cc-notifier..."
echo

# Validate environment
if [ -z "$HOME" ]; then
    echo "❌ HOME environment variable is not set"
    exit 1
fi

# Check if cc-notifier is installed
echo "✅ Checking for existing installation..."
if [ ! -d "$HOME/.cc-notifier" ]; then
    echo "⚠️  cc-notifier is not installed (no ~/.cc-notifier directory found)"
    echo "   Nothing to uninstall."
    exit 0
fi

echo "📦 Found cc-notifier installation at ~/.cc-notifier/"

# Remove main installation directory
echo "📦 Removing installation directory..."
rm -rf "$HOME/.cc-notifier"

# Clean up session files if they exist
if [ -d "/tmp/cc_notifier" ]; then
    echo "🧹 Cleaning up session files..."
    rm -rf "/tmp/cc_notifier"
fi

echo "✅ Removed from ~/.cc-notifier/"
echo

echo "🎯 REQUIRED NEXT STEPS TO COMPLETE REMOVAL:"
echo
echo "1. 🔧 REMOVE CLAUDE CODE HOOKS (Required)"
echo "   Edit ~/.claude/settings.json and remove the cc-notifier hooks"
echo
echo "2. 🔨 REMOVE ANY HAMMERSPOON CONFIGURATION"
echo
echo "3. 📦 OPTIONAL: Remove dependencies if not needed elsewhere"
echo "   These may be used by other applications:"
echo "   • brew uninstall terminal-notifier"
echo "   • brew uninstall --cask hammerspoon"
echo

# Send success notification if terminal-notifier is available
if command -v terminal-notifier >/dev/null 2>&1; then
    echo "📬 Sending success notification..."
    terminal-notifier \
        -title "cc-notifier Uninstalled Successfully!" \
        -message "Check terminal for manual cleanup steps" \
        -sound "Funk" \
        -timeout 10
else
    echo "📬 terminal-notifier not available, skipping notification"
fi

echo "✅ cc-notifier has been uninstalled!"
echo "   Remember to remove the Claude Code hooks from ~/.claude/settings.json"