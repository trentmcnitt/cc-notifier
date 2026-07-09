#!/bin/bash
set -e

echo "🔧 Installing cc-notifier..."
echo

# Validate environment
if [ -z "$HOME" ]; then
    echo "❌ HOME environment variable is not set"
    exit 1
fi

# Check Python 3.9+
echo "✅ Checking Python version..."
python3 -c "import sys; assert sys.version_info >= (3,9), 'Python 3.9+ required'" || {
    echo "❌ Python 3.9+ is required but not found"
    echo "   Install with: brew install python3"
    exit 1
}

# Check required commands
echo "✅ Checking required commands..."
missing_deps=()

for cmd in hs terminal-notifier; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        missing_deps+=("$cmd")
    fi
done

if [ ${#missing_deps[@]} -ne 0 ]; then
    echo "❌ Missing required dependencies:"
    for dep in "${missing_deps[@]}"; do
        case "$dep" in
            "hs")
                echo "   • Hammerspoon CLI - Install with: brew install --cask hammerspoon"
                echo "     Then launch Hammerspoon.app and run hs.ipc.cliInstall() in its console"
                ;;
            "terminal-notifier")
                echo "   • terminal-notifier - Install with: brew install terminal-notifier"
                ;;
            *)
                echo "   • $dep - Unknown dependency"
                ;;
        esac
    done
    echo
    echo "📖 See the README for detailed setup instructions: https://github.com/trentmcnitt/cc-notifier#requirements"
    exit 1
fi

# Verify hs CLI is actually responsive (not just present on PATH).
# A missing/idle Hammerspoon makes `hs -c` hang forever — bound it with perl's
# alarm() since macOS has no portable `timeout` command.
echo "✅ Verifying Hammerspoon CLI is responsive..."
hs_check=$(perl -e 'alarm 5; exec @ARGV' hs -c 'print("ok")' 2>&1 || echo "__HS_FAILED__")
if [ "$hs_check" != "ok" ]; then
    echo "❌ Hammerspoon CLI is not responsive."
    echo
    echo "   The 'hs' command exists, but it couldn't reach a running Hammerspoon."
    echo "   Usually one of:"
    echo "     1. Hammerspoon.app isn't running — launch it from /Applications"
    echo "     2. The CLI shim was never installed — open the Hammerspoon Console"
    echo "        (menu bar icon → Console) and run: hs.ipc.cliInstall()"
    echo
    echo "   Then re-run ./install.sh."
    echo
    echo "📖 See README → Desktop Mode for the full setup sequence."
    exit 1
fi

# Check source files exist
echo "✅ Checking source files..."
for file in cc_notifier.py cc-notifier; do
    if [ ! -f "$file" ]; then
        echo "❌ Source file '$file' not found in current directory"
        echo "   Please run this script from the cc-notifier directory"
        exit 1
    fi
done

# Create installation directory
echo "📦 Creating installation directory..."
mkdir -p ~/.cc-notifier

# Copy files
echo "📦 Installing files..."
cp cc_notifier.py ~/.cc-notifier/
cp cc-notifier ~/.cc-notifier/
chmod +x ~/.cc-notifier/cc_notifier.py
chmod +x ~/.cc-notifier/cc-notifier

echo "✅ Installed to ~/.cc-notifier/"
echo
echo "🎯 REQUIRED NEXT STEPS TO COMPLETE SETUP:"
echo
echo "1. 🔧 CONFIGURE HAMMERSPOON (Required)"
echo "2. ⚙️  ADD TO CLAUDE CODE HOOKS (Required)"
echo
echo "📖 See README for complete configuration details:"
echo "   https://github.com/trentmcnitt/cc-notifier#installation"
echo
echo "cc-notifier will not work until both steps are completed!"

# Send success notification
echo "📬 Sending success notification..."
terminal-notifier \
    -title "cc-notifier Installation Successful!" \
    -message "Check terminal for next steps" \
    -sound "Funk" \
    -timeout 10