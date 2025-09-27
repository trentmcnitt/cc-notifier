#!/usr/bin/env python3
"""Simple testing utility for cc-notifier notifications."""

import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Optional

# Check cc_notifier exists and import functions for isolated testing
try:
    from cc_notifier import (
        HookData,
        PushConfig,
        create_notification_data,
        send_notification,
        send_pushover_notification,
    )
except ImportError:
    print("❌ cc_notifier.py must be in the same directory")
    sys.exit(1)

# Test session data
session_id = f"test-{uuid.uuid4().hex[:8]}"
hook_data = {
    "session_id": session_id,
    "cwd": str(Path.cwd()),
    "hook_event_name": "Stop",
    "message": "Test notification completed successfully!",
}


def get_push_credentials() -> tuple[Optional[str], Optional[str]]:
    """Get push credentials from environment or Claude settings."""
    # Environment variables first
    token, user = os.getenv("PUSHOVER_API_TOKEN"), os.getenv("PUSHOVER_USER_KEY")
    if token and user:
        return token, user

    # Claude settings fallback
    try:
        with open(Path.home() / ".claude" / "settings.json") as f:
            env_vars = json.load(f).get("env", {})
            token, user = (
                env_vars.get("PUSHOVER_API_TOKEN"),
                env_vars.get("PUSHOVER_USER_KEY"),
            )
            return (token, user) if token and user else (None, None)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None, None


def run_command(cmd: str, debug: bool = False) -> None:
    """Run cc-notifier command with test data."""
    env = os.environ.copy()
    # Set wrapper environment variable to allow direct execution of cc_notifier.py
    env["CC_NOTIFIER_WRAPPER"] = "1"
    token, user = get_push_credentials()
    if token and user:
        env.update({"PUSHOVER_API_TOKEN": token, "PUSHOVER_USER_KEY": user})

    command_args = ["python3", "cc_notifier.py"]
    if debug:
        command_args.append("--debug")
    command_args.append(cmd)

    try:
        result = subprocess.run(
            command_args,
            input=json.dumps(hook_data),
            text=True,
            capture_output=True,
            env=env,
        )
        if result.returncode != 0:
            print(f"❌ Command '{cmd}' failed: {result.stderr.strip()}")
        if debug and result.stdout:
            print(f"🔍 Debug output: {result.stdout.strip()}")
    except Exception as e:
        print(f"❌ Command '{cmd}' failed: {e}")


def cleanup(debug: bool = False) -> None:
    """Clean up test session."""
    print("\n🧹 Cleaning up...")
    run_command("cleanup", debug)


def test_notification(
    title: str, test_hook_data: HookData, push_only: bool = False, debug: bool = False
) -> None:
    """Common notification testing logic."""
    title, subtitle, message = create_notification_data(test_hook_data)

    if push_only:
        # Test push notification only
        token, user = get_push_credentials()
        if not token or not user:
            print("❌ Push notifications disabled - missing credentials")
            return

        print("📲 Sending test push notification...")
        push_config = PushConfig(token=token, user=user)
        current_time = time.strftime("%I:%M %p").lstrip("0")
        success = send_pushover_notification(
            push_config, f"{subtitle} 🔔 {current_time}", message
        )
        print(
            "✅ Push notification sent!" if success else "❌ Push notification failed"
        )
    else:
        # Test local notification with optional debug formatting
        print("📱 Sending test local notification...")
        if debug:
            # Apply debug formatting like cc_notifier.py does
            now = time.time()
            dt = time.localtime(now)
            milliseconds = int((now % 1) * 1000)
            current_time = f"{time.strftime('%H:%M:%S', dt)}.{milliseconds:03d}"
            title = f"[DEBUG] {title} [{current_time}]"
            print(f"🔍 Debug title: {title}")

        try:
            send_notification(title=title, subtitle=subtitle, message=message)
            print("✅ Local notification sent! Check your notification center")
        except Exception as e:
            print(f"❌ Local notification failed: {e}")


def test_system_mode(debug: bool = False) -> None:
    """Test full Claude Code hook emulation."""
    print(f"🔧 Testing cc-notifier (Session: {session_id})")
    if debug:
        print("🐛 Debug mode ENABLED - detailed logging active")

    # Check push configuration
    push_token, push_user = get_push_credentials()
    status = "✅ ENABLED" if push_token and push_user else "❌ DISABLED"
    print(f"📲 Push notifications: {status}")
    if not push_token or not push_user:
        print(
            "   Set PUSHOVER_API_TOKEN and PUSHOVER_USER_KEY in environment or ~/.claude/settings.json"
        )

    print("💡 Switch to another app during countdown to see notification\n")

    # Initialize and run test
    run_command("init", debug)
    print("✅ Session initialized - switch away now!")

    # Countdown and notify
    print("⏱️  Checking for notification in ", end="", flush=True)
    for i in range(5, 0, -1):
        print(f"{i}...", end="", flush=True)
        time.sleep(1)
    print(" NOW!")

    print("📢 Sending notification if window focus changed...")
    run_command("notify", debug)
    time.sleep(3)
    cleanup(debug)


def test_push_only() -> None:
    """Test push notifications only."""
    print("🧪 Testing push notifications only...")
    test_hook_data = HookData(
        session_id=session_id,
        cwd=str(Path.cwd()),
        message="Push notification test successful!",
    )
    test_notification("Claude Code 🔔 (Test)", test_hook_data, push_only=True)


def test_local_only(debug: bool = False) -> None:
    """Test local notifications only."""
    print("🧪 Testing local notifications only...")
    if debug:
        print("🐛 Debug mode ENABLED - notification will show debug timestamp")
    test_hook_data = HookData(
        session_id=session_id,
        cwd=str(Path.cwd()),
        message="Local notification test successful!",
    )
    test_notification("Claude Code 🔔 (Test)", test_hook_data, debug=debug)


def show_help() -> None:
    """Display help information."""
    print("🔧 cc-notifier Test Utility\n")
    print("Usage: python3 manual_testing.py <mode> [--debug]\n")
    print("Modes:")
    print("  local    - Test local notifications only")
    print("  push     - Test push notifications only (requires credentials)")
    print("  system   - Full Claude Code hook emulation")
    print("\nOptions:")
    print(
        "  --debug  - Enable debug mode with detailed logging and timestamped notifications"
    )


if __name__ == "__main__":
    debug = False  # Initialize debug variable
    try:
        # Parse arguments
        debug = "--debug" in sys.argv
        if debug:
            sys.argv.remove("--debug")

        if len(sys.argv) != 2 or sys.argv[1] in ("-h", "--help", "help"):
            show_help()
            sys.exit(0 if len(sys.argv) == 2 else 1)

        mode = sys.argv[1]
        if mode == "push":
            test_push_only()
        elif mode == "local":
            test_local_only(debug=debug)
        elif mode == "system":
            test_system_mode(debug=debug)
        else:
            print(f"❌ Unknown mode: {mode}")
            show_help()
            sys.exit(1)
    except KeyboardInterrupt:
        cleanup(debug)
        sys.exit(0)
