#!/bin/bash
set -e

echo "🔧 Installing cc-notifier..."
echo

# Validate environment
if [ -z "$HOME" ]; then
    echo "❌ HOME environment variable is not set"
    exit 1
fi

# Check Python 3.7+
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
                echo "     After installing, ensure Hammerspoon is running and CLI is enabled"
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
    echo "📖 See the README for detailed setup instructions: https://github.com/Rendann/cc-notifier#requirements"
    exit 1
fi

# Hammerspoon setup reminder
echo "⚠️  Remember to setup Hammerspoon"
echo "   See README section: 🔧 Hammerspoon Setup"

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
echo "   https://github.com/Rendann/cc-notifier#installation"
echo
echo "cc-notifier will not work until both steps are completed!"

# Send success notification
echo "📬 Sending success notification..."
terminal-notifier \
    -title "cc-notifier Installation Successful!" \
    -message "Check terminal for next steps" \
    -sound "Funk" \
    -timeout 10