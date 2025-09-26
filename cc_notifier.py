#!/usr/bin/env python3
"""
cc-notifier - macOS notification system for Claude Code hooks

Note to AI: YOU MUST READ ./cc_notifier.context.md BEFORE ANALYZING OR WORKING WITH THIS FILE. It contains important details about this file.
"""

import fcntl
import json
import os
import shlex
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

# Constants and configuration
VERSION = "0.2.0"
SESSION_DIR = Path("/tmp/cc_notifier")
CLEANUP_AGE_SECONDS = 5 * 24 * 60 * 60
NOTIFICATION_DEDUPLICATION_THRESHOLD_SECONDS = 2.0
MAX_LOG_LINES = 2250  # Trigger trim when exceeded
TRIM_TO_LINES = 1250  # Keep newest lines after trim
HAMMERSPOON_CLI = "/Applications/Hammerspoon.app/Contents/Frameworks/hs/hs"
TERMINAL_NOTIFIER = "/opt/homebrew/bin/terminal-notifier"
DEFAULT_IDLE_CHECK_INTERVALS = [3]  # Shortened for testing

# Debug configuration
DEBUG = False


def handle_command_errors(
    command_name: str,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to handle command errors with consistent logging and exit."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                log_error(f"Command '{command_name}' failed", e)
                sys.exit(1)

        return wrapper

    return decorator


# ============================================================================
# COMMAND LINE INTERFACE - Main Entry Point and Command Dispatch
# ============================================================================


def main() -> None:
    """Main entry point for cc-notifier command."""

    global DEBUG
    if "--debug" in sys.argv:
        DEBUG = True
        sys.argv.remove("--debug")

    command = sys.argv[1] if len(sys.argv) > 1 else "help"
    debug_log(f"Command: {command}")
    if command in ("--version", "-v"):
        print(f"cc-notifier {VERSION}")
    elif command == "init":
        cmd_init()
    elif command == "notify":
        cmd_notify()
    elif command == "cleanup":
        cmd_cleanup()
    else:
        show_help()
        sys.exit(1)


@handle_command_errors("init")
def cmd_init() -> None:
    """Initialize session by capturing focused window ID."""
    hook_data = HookData.from_stdin()
    window_id = get_focused_window_id()
    save_window_id(hook_data.session_id, window_id)


@handle_command_errors("notify")
def cmd_notify() -> None:
    """Send intelligent notification if user switched away from original window."""
    hook_data = HookData.from_stdin()
    session_file = SESSION_DIR / hook_data.session_id

    if check_deduplication(session_file):
        return

    original_window_id = session_file.read_text().strip().split("\n")[0]
    send_local_notification_if_needed(hook_data, original_window_id)
    if os.getenv("PUSHOVER_API_TOKEN") and os.getenv("PUSHOVER_USER_KEY"):
        debug_log("Checking for push notification")
        check_idle_and_notify_push(hook_data, DEFAULT_IDLE_CHECK_INTERVALS)


@handle_command_errors("cleanup")
def cmd_cleanup() -> None:
    """Clean up session files and perform age-based maintenance."""
    hook_data = HookData.from_stdin()
    cleanup_session(hook_data.session_id)


def show_help() -> None:
    """Display help information."""
    print(f"""cc-notifier {VERSION}

Usage: cc-notifier [--debug] {{init|notify|cleanup|--version}}

Commands:
  init     - Initialize session (capture focused window)
  notify   - Send notification if user switched away (local + push)
  cleanup  - Clean up session files
  --version - Show version information

Options:
  --debug  - Enable debug logging with timestamps

macOS notification system for Claude Code hooks with push notification support.
Set PUSHOVER_API_TOKEN and PUSHOVER_USER_KEY to enable push notifications.""")


# ============================================================================
# CORE UTILITIES - Session Management and Data Structures
# ============================================================================


@dataclass
class HookData:
    """Data structure for Claude Code hook events."""

    session_id: str
    cwd: str = ""
    hook_event_name: str = "Stop"
    message: str = ""

    @classmethod
    def from_stdin(cls) -> "HookData":
        """Parse hook data from JSON stdin input."""
        try:
            data = json.loads(sys.stdin.read())
            valid_fields = {"session_id", "cwd", "hook_event_name", "message"}
            filtered_data = {k: v for k, v in data.items() if k in valid_fields and v}
            hook_data = cls(**filtered_data)
            debug_log(f"Hook: {hook_data.session_id}, {hook_data.hook_event_name}")
            return hook_data
        except json.JSONDecodeError as err:
            raise ValueError("Invalid JSON input from stdin") from err


def check_deduplication(session_file: Path) -> bool:
    """Check if notification should be deduplicated. Returns True if should skip."""
    try:
        with open(session_file, "r+") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            lines = f.read().strip().split("\n")
            if (
                time.time() - float(lines[1])
                < NOTIFICATION_DEDUPLICATION_THRESHOLD_SECONDS
            ):
                return True
            # Update timestamp immediately to prevent race condition
            f.seek(0)
            f.write(f"{lines[0]}\n{time.time()}")
            f.truncate()
            return False
    except BlockingIOError:
        return True


def send_local_notification_if_needed(
    hook_data: HookData, original_window_id: str
) -> None:
    """Send local notification if user switched away from original window."""
    current_window_id = get_focused_window_id()

    if original_window_id == current_window_id:
        debug_log("User still on original window - no local notification needed")
        return

    # User switched away - send local notification
    title, subtitle, message = create_notification_data(hook_data)

    debug_log(
        f"Sending local notification: original_window={original_window_id}, current_window={current_window_id}, notification='{title}' | '{subtitle}' | '{message}'"
    )

    send_notification(
        title=title,
        subtitle=subtitle,
        message=message,
        focus_window_id=original_window_id,
    )


def save_window_id(session_id: str, window_id: str) -> None:
    """Save window ID to session file."""
    SESSION_DIR.mkdir(exist_ok=True)
    session_file = SESSION_DIR / session_id
    session_file.write_text(f"{window_id}\n0")
    debug_log(
        f"Session initialized: window_id={window_id}, session_file={session_file}"
    )


def load_window_id(session_id: str) -> str:
    """Load window ID from session file."""
    session_file = SESSION_DIR / session_id
    lines = session_file.read_text().strip().split("\n")
    window_id = lines[0]
    debug_log(f"Session restored: window_id={window_id}, session_file={session_file}")
    return window_id


def cleanup_session(_: str) -> None:
    """Clean up session files and perform age-based maintenance."""
    # Skip session-specific deletion due to Claude Code bug #7911 (session ID mismatch)
    cutoff_time = time.time() - CLEANUP_AGE_SECONDS
    cleaned_files = 0
    for file_path in SESSION_DIR.glob("*"):
        if not file_path.is_file():
            continue
        try:
            if file_path.stat().st_mtime < cutoff_time:
                file_path.unlink(missing_ok=True)
                cleaned_files += 1
        except OSError:
            continue

    if cleaned_files > 0 or DEBUG:
        debug_log(
            f"Session cleanup completed: removed {cleaned_files} old session files"
        )


LOG_FILE = Path.home() / ".cc-notifier" / "cc-notifier.log"


def _trim_log_if_needed() -> None:
    """Trim log file if over MAX_LOG_LINES."""
    if not LOG_FILE.exists() or sum(1 for _ in LOG_FILE.open()) <= MAX_LOG_LINES:
        return
    lines = LOG_FILE.read_text().splitlines()
    LOG_FILE.write_text("\n".join(lines[-TRIM_TO_LINES:]) + "\n")


def _write_log_entry(
    level: str, message: str, exception: Optional[Exception] = None
) -> None:
    """Write log entry with automatic trimming."""
    LOG_FILE.parent.mkdir(exist_ok=True)
    _trim_log_if_needed()

    entry = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [{level}] {message}"
    if exception:
        entry += f" - {type(exception).__name__}: {exception}"

    LOG_FILE.write_text(
        LOG_FILE.read_text() + entry + "\n" if LOG_FILE.exists() else entry + "\n"
    )


def debug_log(message: str) -> None:
    """Log debug message when DEBUG is enabled."""
    if DEBUG:
        _write_log_entry("DEBUG", message)


def log_error(error_msg: str, exception: Optional[Exception] = None) -> None:
    """Log errors to file and send notification."""
    _write_log_entry("ERROR", error_msg, exception)

    # Send error notification with fallback
    try:
        run_background_command(
            [
                TERMINAL_NOTIFIER,
                "-title",
                "cc-notifier Error",
                "-message",
                error_msg,
                "-sound",
                "Basso",
                "-execute",
                f"open {LOG_FILE}",
            ]
        )
    except Exception:
        run_background_command(
            [
                "osascript",
                "-e",
                f'display notification "{error_msg}" with title "cc-notifier Error" sound name "Basso"',
            ]
        )


# ============================================================================
# HAMMERSPOON INTEGRATION - Cross-Space Window Management
# ============================================================================


def get_focused_window_id() -> str:
    """Get the currently focused window ID using Hammerspoon CLI."""
    try:
        window_id = run_command(
            [
                HAMMERSPOON_CLI,
                "-c",
                "local w=hs.window.focusedWindow(); print(w and w:id() or 'ERROR')",
            ]
        )
        if window_id == "ERROR" or not window_id:
            raise RuntimeError("Failed to get focused window ID from Hammerspoon")
        return window_id
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(
            f"Hammerspoon command timed out after {e.timeout} seconds"
        ) from e


def create_focus_command(window_id: str) -> list[str]:
    """
    Create the Hammerspoon focus command for cross-space window focusing.

    This uses a dual-filter approach to avoid infinite hangs that occur
    with setCurrentSpace(nil). The approach combines windows from current
    and other spaces, then searches for the target window ID.

    Args:
        window_id: The window ID to focus

    Returns:
        List of command arguments for subprocess execution
    """
    # Template for complex dual-filter cross-space window focusing
    # This solves the macOS Spaces issue without using setCurrentSpace(nil) which causes hangs
    focus_script = f"""local current = require('hs.window.filter').new():setCurrentSpace(true):getWindows()
local other = require('hs.window.filter').new():setCurrentSpace(false):getWindows()
for _,w in pairs(other) do table.insert(current, w) end
for _,w in pairs(current) do
  if w:id()=={window_id} then
    w:focus()
    require('hs.timer').usleep(300000)
    return
  end
end"""
    return [HAMMERSPOON_CLI, "-c", focus_script]


# ============================================================================
# NOTIFICATION SYSTEM - macOS Notifications with Click-to-Focus
# ============================================================================


def create_notification_data(
    hook_data: HookData, for_push: bool = False
) -> tuple[str, str, str]:
    """Create complete notification data (title, subtitle, message)."""
    # Generate subtitle and message
    subtitle = Path(hook_data.cwd).name if hook_data.cwd else "Task Completed"
    message = (
        hook_data.message
        if (hook_data.hook_event_name == "Notification" and hook_data.message)
        else "Completed task"
    )

    # Generate title
    if for_push:
        title = subtitle
        if DEBUG:
            now = time.time()
            dt = time.localtime(now)
            milliseconds = int((now % 1) * 1000)
            timestamp = f"{time.strftime('%H:%M:%S', dt)}.{milliseconds:03d}"
        else:
            timestamp = time.strftime("%I:%M %p").lstrip("0")
        title = f"{title} [{timestamp}]"
    else:
        title = "Claude Code 🔔"
        if DEBUG:
            title = f"\\[DEBUG] {title}"

    return title, subtitle, message


def send_notification(
    title: str, subtitle: str, message: str, focus_window_id: Optional[str] = None
) -> None:
    """Send a macOS notification with optional click-to-focus functionality."""
    cmd = [
        TERMINAL_NOTIFIER,
        "-title",
        title,
        "-subtitle",
        subtitle,
        "-message",
        message,
        "-sound",
        "Glass",
        "-ignoreDnD",
    ]

    # Add click-to-focus functionality if window ID provided
    if focus_window_id:
        focus_cmd = create_focus_command(focus_window_id)
        execute_cmd = " ".join(shlex.quote(arg) for arg in focus_cmd)
        cmd.extend(["-execute", execute_cmd])

    # Send notification in background
    try:
        run_background_command(cmd)
        if DEBUG:
            debug_log(f"Notification sent: focus_window_id={focus_window_id}")
    except Exception as e:
        debug_log(f"Notification failed: {type(e).__name__}")
        raise


# ============================================================================
# PUSH NOTIFICATIONS - Idle Detection and Pushover Integration
# API Documentation: https://pushover.net/api
# ============================================================================


@dataclass
class PushConfig:
    """Push notification service configuration."""

    token: str
    user: str

    @classmethod
    def from_env(cls) -> Optional["PushConfig"]:
        """Create PushConfig from environment variables."""
        token = os.getenv("PUSHOVER_API_TOKEN")
        user = os.getenv("PUSHOVER_USER_KEY")

        if token and user:
            return cls(token=token, user=user)
        return None


def send_pushover_notification(config: PushConfig, title: str, message: str) -> bool:
    """Send notification via Pushover API.

    Returns:
        True if Pushover API returned {"status":1}, False otherwise.
        Handles network errors, JSON parsing errors, and API failures gracefully.
    """
    # Enforce Pushover API limits: 250 char title, 1024 char message
    title = title[:250] if len(title) > 250 else title
    message = message[:1024] if len(message) > 1024 else message

    data = urllib.parse.urlencode(
        {
            "token": config.token,
            "user": config.user,
            "title": title,
            "message": message,
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        "https://api.pushover.net/1/messages.json",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                response_data = json.loads(response.read().decode("utf-8"))
                success = bool(response_data.get("status") == 1)
                debug_log(
                    f"Push notification result: status={response.status}, success={success}"
                )
                return success
            debug_log(
                f"Push notification result: status={response.status}, success=False"
            )
            return False
    except (urllib.error.URLError, json.JSONDecodeError, KeyError) as e:
        debug_log(f"Push notification result: error={type(e).__name__}, success=False")
        return False


def get_idle_time() -> int:
    """Get macOS system idle time in seconds using ioreg."""
    try:
        output = run_command(["ioreg", "-c", "IOHIDSystem"], timeout=5)
        for line in output.splitlines():
            if "HIDIdleTime" in line:
                idle_nanoseconds = int(line.split("=", 1)[1].strip())
                return idle_nanoseconds // 1_000_000_000
        raise RuntimeError("HIDIdleTime not found in ioreg output")
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"ioreg command timed out after {e.timeout} seconds") from e


def is_user_idle(seconds: int) -> bool:
    """Check if user has been idle for specified duration."""
    try:
        return bool(get_idle_time() >= seconds)
    except RuntimeError:
        return False  # Assume user is active if detection fails


def check_idle_and_notify_push(hook_data: HookData, check_times: list[int]) -> None:
    """Check if user is idle at specified intervals and send push notification if away."""
    push_config = PushConfig.from_env()
    if not push_config:
        return

    if not check_times:
        raise ValueError("check_times cannot be empty")

    previous_time = 0
    for check_time in check_times:
        time.sleep(check_time - previous_time)
        if not is_user_idle(check_time):
            return  # User became active, exit early
        previous_time = check_time

    # User has been idle through all checks, send push notification
    title, _, message = create_notification_data(hook_data, for_push=True)

    debug_log(f"Sending push notification: '{title}'")
    send_pushover_notification(push_config, title, message)


# ============================================================================
# SUBPROCESS UTILITIES - Common patterns for external command execution
# ============================================================================


def run_command(cmd: list[str], timeout: int = 10) -> str:
    """Run command and return stdout, raising RuntimeError on failure."""
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}")
    return result.stdout.strip()


def run_background_command(cmd: list[str]) -> None:
    """Run command in background (non-blocking)."""
    subprocess.Popen(cmd)


if __name__ == "__main__":
    main()
