#!/usr/bin/env python3
"""Test script to demonstrate Hammerspoon error notification when window focus fails."""

import shlex
import subprocess

HAMMERSPOON_CLI = "/Applications/Hammerspoon.app/Contents/Frameworks/hs/hs"
TERMINAL_NOTIFIER = "/opt/homebrew/bin/terminal-notifier"
FAKE_WINDOW_ID = "99999999"

print("🧪 Testing cc-notifier focus failure notification...")
print()
print("This will send a test notification. When you click it, Hammerspoon will")
print("fail to find the window and show an error notification with helpful advice.")
print()

# Create focus script matching cc_notifier.py implementation
focus_script = f"""local current = require('hs.window.filter').new():setCurrentSpace(true):getWindows()
local other = require('hs.window.filter').new():setCurrentSpace(false):getWindows()
for _,w in pairs(other) do table.insert(current, w) end
for _,w in pairs(current) do
  if w:id()=={FAKE_WINDOW_ID} then
    w:focus()
    require('hs.timer').usleep(300000)
    return
  end
end
require('hs.notify').new({{title="cc-notifier", informativeText="Could not restore window focus. Try reopening your terminal or IDE.", soundName="Basso"}}):send()"""

focus_cmd = [HAMMERSPOON_CLI, "-c", focus_script]
execute_cmd = " ".join(shlex.quote(arg) for arg in focus_cmd)

print("📱 Sending test notification...")
subprocess.Popen(
    [
        TERMINAL_NOTIFIER,
        "-title",
        "Click to Test Focus Failure",
        "-subtitle",
        "cc-notifier Test",
        "-message",
        "Click this notification to see the error notification.",
        "-sound",
        "Glass",
        "-execute",
        execute_cmd,
    ]
)

print("✅ Test notification sent! Click it to see the error notification.")
