"""
Core functionality tests for cc-notifier.

Tests CLI interface, core workflows, data parsing, and session file operations.
Focuses on essential user-facing behaviors that must work reliably.
"""

import json
import os
import subprocess
import sys
import tempfile
import time
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

import cc_notifier


class TestCLIInterface:
    """Test command line interface and command routing."""

    def test_main_with_no_args_exits_with_error(self, capsys):
        """Test main() exits with error when no command provided."""
        with (
            pytest.raises(SystemExit) as exc_info,
            patch.object(sys, "argv", ["cc-notifier"]),
            patch.dict(os.environ, {"CC_NOTIFIER_WRAPPER": "1"}),
        ):
            cc_notifier.main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Usage:" in captured.out

    def test_main_with_invalid_command_exits_with_error(self, capsys):
        """Test main() exits with error for unknown commands."""
        with (
            pytest.raises(SystemExit) as exc_info,
            patch.object(sys, "argv", ["cc-notifier", "invalid"]),
            patch.dict(os.environ, {"CC_NOTIFIER_WRAPPER": "1"}),
        ):
            cc_notifier.main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Usage:" in captured.out

    def test_main_version_flag_shows_version(self, capsys):
        """Test --version and -v flags return correct version."""
        for flag in ["--version", "-v"]:
            with (
                patch.object(sys, "argv", ["cc-notifier", flag]),
                patch.dict(os.environ, {"CC_NOTIFIER_WRAPPER": "1"}),
            ):
                cc_notifier.main()

            captured = capsys.readouterr()
            assert f"cc-notifier {cc_notifier.VERSION}" in captured.out

    def test_main_exception_handling_exits_with_status_1(self):
        """Test main() catches exceptions and exits with status 1."""
        with (
            patch.object(sys, "argv", ["cc-notifier", "init"]),
            patch.dict(os.environ, {"CC_NOTIFIER_WRAPPER": "1"}),
            patch(
                "cc_notifier.HookData.from_stdin", side_effect=ValueError("Test error")
            ),
            patch("cc_notifier.run_background_command"),
            pytest.raises(SystemExit) as exc_info,
        ):
            cc_notifier.main()

        assert exc_info.value.code == 1

    def test_debug_flag_parsing(self, tmp_path):
        """Test debug flag enables logging and is properly removed from argv."""
        original_debug = cc_notifier.DEBUG

        try:
            # Reset debug state
            cc_notifier.DEBUG = False

            # Mock the init command to avoid actual Hammerspoon calls
            with (
                patch.object(sys, "argv", ["cc-notifier", "--debug", "init"]),
                patch("cc_notifier.HookData.from_stdin") as mock_stdin,
                patch("cc_notifier.get_focused_window_id") as mock_window,
                patch("cc_notifier.get_tmux_session_id", return_value=None),
                patch("cc_notifier.save_window_id") as mock_save,
                patch.dict(os.environ, {"CC_NOTIFIER_WRAPPER": "1"}),
            ):
                # Setup mocks to allow init to complete
                mock_stdin.return_value = cc_notifier.HookData(session_id="test")
                mock_window.return_value = (
                    "12345",
                    "/System/Applications/Utilities/Terminal.app",
                )

                # Test actual main() call with debug flag
                cc_notifier.main()

                # Verify debug flag was processed and enabled logging
                assert cc_notifier.DEBUG is True

                # Verify the underlying command executed (init was called)
                mock_stdin.assert_called_once()
                mock_window.assert_called_once()
                mock_save.assert_called_once_with(
                    "test", "12345", "/System/Applications/Utilities/Terminal.app", ""
                )

        finally:
            # Restore original state
            cc_notifier.DEBUG = original_debug

    def test_main_exception_logged_and_exits_1(self, tmp_path):
        """Test main() logs real command errors and exits with status 1."""
        log_file = tmp_path / ".cc-notifier" / "cc-notifier.log"

        with (
            patch.object(cc_notifier, "LOG_FILE", log_file),
            patch("sys.argv", ["cc-notifier", "init"]),
            patch("sys.stdin.read", side_effect=ValueError("Test error")),
            patch("cc_notifier.run_background_command"),
            patch.dict(os.environ, {"CC_NOTIFIER_WRAPPER": "1"}),
            pytest.raises(SystemExit) as exc_info,
        ):
            cc_notifier.main()

        assert exc_info.value.code == 1

        # Verify real log file was created with error content
        assert log_file.exists()
        content = log_file.read_text()
        assert "Command 'init' failed" in content
        assert "ValueError: Test error" in content

    def test_notify_continues_to_push_when_local_fails(self, tmp_path):
        """Test notify gracefully handles local notification failure and continues to push."""
        session_dir = tmp_path / "cc_notifier"
        session_dir.mkdir()
        (session_dir / "test").write_text(
            "12345\n/System/Applications/Utilities/Terminal.app\n0\n"
        )

        with (
            patch.object(cc_notifier, "SESSION_DIR", session_dir),
            patch("sys.argv", ["cc-notifier", "notify"]),
            patch("sys.stdin.read", return_value='{"session_id": "test"}'),
            patch(
                "cc_notifier.get_focused_window_id",
                side_effect=RuntimeError("Hammerspoon not found"),
            ),
            patch("cc_notifier.check_idle_and_notify_push") as mock_push,
            patch(
                "cc_notifier.PushConfig.from_env",
                return_value=cc_notifier.PushConfig(token="test", user="test"),
            ),
            patch.dict(os.environ, {"CC_NOTIFIER_WRAPPER": "1"}),
        ):
            # Should not raise - local failure is caught
            cc_notifier.main()

        # Push notification path was reached despite local failure
        mock_push.assert_called_once()

    def test_main_blocks_direct_execution_without_wrapper_env(self, capsys):
        """Test main() blocks execution without CC_NOTIFIER_WRAPPER environment variable."""
        with (
            pytest.raises(SystemExit) as exc_info,
            patch.object(sys, "argv", ["cc-notifier", "--version"]),
            patch.dict(os.environ, {}, clear=True),  # Clear environment
        ):
            cc_notifier.main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert (
            "ERROR: cc_notifier.py should not be run directly in Claude Code hooks."
            in captured.err
        )
        assert "Use: cc-notifier wrapper instead" in captured.err
        assert "Running directly will block Claude Code execution!" in captured.err

    def test_main_allows_execution_with_wrapper_env(self, capsys):
        """Test main() allows execution when CC_NOTIFIER_WRAPPER is set."""
        with (
            patch.object(sys, "argv", ["cc-notifier", "--version"]),
            patch.dict(os.environ, {"CC_NOTIFIER_WRAPPER": "1"}),
        ):
            cc_notifier.main()

        captured = capsys.readouterr()
        assert f"cc-notifier {cc_notifier.VERSION}" in captured.out


class TestCoreWorkflows:
    """Test complete command workflows end-to-end."""

    def test_init_workflow_captures_and_saves_window(self, tmp_path):
        """Test complete init workflow: JSON input → window capture → real file save."""
        test_input = {"session_id": "workflow123", "cwd": "/test/path"}
        session_dir = tmp_path / "cc_notifier"

        with (
            patch(
                "cc_notifier.get_focused_window_id",
                return_value=("54321", "/Applications/Visual Studio Code.app"),
            ),
            patch("cc_notifier.get_tmux_session_id", return_value="$20"),
            patch("sys.stdin", StringIO(json.dumps(test_input))),
            patch.object(sys, "argv", ["cc-notifier", "init"]),
            patch.object(cc_notifier, "SESSION_DIR", session_dir),
            patch.dict(os.environ, {"CC_NOTIFIER_WRAPPER": "1"}),
        ):
            cc_notifier.main()

        # Verify real end-to-end workflow behavior
        session_file = session_dir / "workflow123"
        assert session_file.exists()
        lines = session_file.read_text().strip().split("\n")
        assert lines[0] == "54321"
        assert lines[1] == "/Applications/Visual Studio Code.app"
        assert lines[2] == "0"
        assert lines[3] == "$20"  # tmux session ID captured

    def test_init_workflow_without_hammerspoon(self, tmp_path):
        """Test init falls back to UNAVAILABLE but still captures tmux session ID."""
        test_input = {"session_id": "nohammer", "cwd": "/test/path"}
        session_dir = tmp_path / "cc_notifier"

        with (
            patch(
                "cc_notifier.get_focused_window_id",
                side_effect=RuntimeError("Hammerspoon not found"),
            ),
            patch("cc_notifier.get_tmux_session_id", return_value="$5"),
            patch("sys.stdin", StringIO(json.dumps(test_input))),
            patch.object(sys, "argv", ["cc-notifier", "init"]),
            patch.object(cc_notifier, "SESSION_DIR", session_dir),
            patch.dict(os.environ, {"CC_NOTIFIER_WRAPPER": "1"}),
        ):
            cc_notifier.main()

        session_file = session_dir / "nohammer"
        assert session_file.exists()
        lines = session_file.read_text().strip().split("\n")
        assert lines[0] == "UNAVAILABLE"
        assert lines[1] == "UNAVAILABLE"
        assert lines[2] == "0"
        assert lines[3] == "$5"  # tmux session ID still captured

    def test_notify_suppressed_when_tmux_attached_without_hammerspoon(self, tmp_path):
        """Test notify suppresses local notification when tmux session is attached."""
        test_input = {"session_id": "nohammer", "cwd": "/test/project"}
        session_dir = tmp_path / "cc_notifier"
        session_dir.mkdir()
        (session_dir / "nohammer").write_text("UNAVAILABLE\nUNAVAILABLE\n0\n$20")

        with (
            patch("cc_notifier.run_background_command") as mock_bg,
            patch("cc_notifier.is_tmux_session_attached", return_value=True),
            patch("sys.stdin", StringIO(json.dumps(test_input))),
            patch.object(sys, "argv", ["cc-notifier", "notify"]),
            patch.object(cc_notifier, "SESSION_DIR", session_dir),
            patch("cc_notifier.PushConfig.from_env", return_value=None),
            patch.dict(os.environ, {"CC_NOTIFIER_WRAPPER": "1"}),
        ):
            cc_notifier.main()

        # No terminal-notifier call (notification suppressed)
        mock_bg.assert_not_called()

    def test_notify_sent_when_tmux_detached_without_hammerspoon(self, tmp_path):
        """Test notify sends local notification when tmux session is detached."""
        test_input = {"session_id": "nohammer", "cwd": "/test/project"}
        session_dir = tmp_path / "cc_notifier"
        session_dir.mkdir()
        (session_dir / "nohammer").write_text("UNAVAILABLE\nUNAVAILABLE\n0\n$20")

        with (
            patch("cc_notifier.run_background_command") as mock_bg,
            patch("cc_notifier.is_tmux_session_attached", return_value=False),
            patch("sys.stdin", StringIO(json.dumps(test_input))),
            patch.object(sys, "argv", ["cc-notifier", "notify"]),
            patch.object(cc_notifier, "SESSION_DIR", session_dir),
            patch("cc_notifier.PushConfig.from_env", return_value=None),
            patch.dict(os.environ, {"CC_NOTIFIER_WRAPPER": "1"}),
        ):
            cc_notifier.main()

        # Notification was sent (tmux detached, no window comparison)
        assert mock_bg.call_count >= 1
        bg_calls = [call[0][0] for call in mock_bg.call_args_list]
        terminal_notifier_calls = [
            cmd
            for cmd in bg_calls
            if any("terminal-notifier" in str(arg) for arg in cmd)
        ]
        assert len(terminal_notifier_calls) >= 1

        # No focus_window_id passed (no -execute in command)
        cmd = terminal_notifier_calls[0]
        assert "-execute" not in cmd

    def test_notify_sent_without_hammerspoon_or_tmux(self, tmp_path):
        """Test notify sends local notification unconditionally when no tmux session."""
        test_input = {"session_id": "nohammer", "cwd": "/test/project"}
        session_dir = tmp_path / "cc_notifier"
        session_dir.mkdir()
        (session_dir / "nohammer").write_text("UNAVAILABLE\nUNAVAILABLE\n0\n")

        with (
            patch("cc_notifier.run_background_command") as mock_bg,
            patch("sys.stdin", StringIO(json.dumps(test_input))),
            patch.object(sys, "argv", ["cc-notifier", "notify"]),
            patch.object(cc_notifier, "SESSION_DIR", session_dir),
            patch("cc_notifier.PushConfig.from_env", return_value=None),
            patch.dict(os.environ, {"CC_NOTIFIER_WRAPPER": "1"}),
        ):
            cc_notifier.main()

        # Notification was sent (no tmux, no window comparison)
        assert mock_bg.call_count >= 1
        bg_calls = [call[0][0] for call in mock_bg.call_args_list]
        terminal_notifier_calls = [
            cmd
            for cmd in bg_calls
            if any("terminal-notifier" in str(arg) for arg in cmd)
        ]
        assert len(terminal_notifier_calls) >= 1

    def test_notify_workflow_user_switched_sends_notification(self, tmp_path):
        """Test notify workflow when user switched: JSON input → file read → real notification."""
        test_input = {"session_id": "notify123", "cwd": "/test/project"}
        # Create session file (window_id + app_name + old timestamp + tmux_session_id)
        session_dir = tmp_path / "cc_notifier"
        session_dir.mkdir()
        (session_dir / "notify123").write_text(
            "original123\n/System/Applications/Utilities/Terminal.app\n0\n"
        )

        env = {"CC_NOTIFIER_WRAPPER": "1"}
        # Ensure custom title format doesn't leak from host environment
        env["CC_NOTIFIER_TITLE_FORMAT"] = ""

        with (
            patch(
                "cc_notifier.get_focused_window_id",
                return_value=("different456", "/Applications/Google Chrome.app"),
            ),
            patch("cc_notifier.run_background_command") as mock_bg,
            patch("sys.stdin", StringIO(json.dumps(test_input))),
            patch.object(sys, "argv", ["cc-notifier", "notify"]),
            patch.object(cc_notifier, "SESSION_DIR", session_dir),
            patch("cc_notifier.PushConfig.from_env", return_value=None),
            patch.dict(os.environ, env),
        ):
            cc_notifier.main()

        # Verify real end-to-end workflow behavior
        # 1. Notification subprocess was started
        assert mock_bg.call_count >= 1
        # 2. Verify terminal-notifier command was called
        bg_calls = [call[0][0] for call in mock_bg.call_args_list]
        terminal_notifier_calls = [
            cmd
            for cmd in bg_calls
            if any("terminal-notifier" in str(arg) for arg in cmd)
        ]
        assert len(terminal_notifier_calls) >= 1
        # 3. Session file timestamp was updated
        content = (session_dir / "notify123").read_text().strip()
        lines = content.split("\n")
        assert lines[0] == "original123"  # Window ID unchanged
        assert (
            lines[1] == "/System/Applications/Utilities/Terminal.app"
        )  # App path unchanged
        assert float(lines[2]) > 0  # Timestamp updated

    def test_notify_workflow_user_stayed_no_notification(self, tmp_path):
        """Test notify workflow when user stayed: JSON input → file read → no notification."""
        test_input = {"session_id": "notify123"}
        # Create session file (window_id + app_name + old timestamp + tmux_session_id)
        session_dir = tmp_path / "cc_notifier"
        session_dir.mkdir()
        (session_dir / "notify123").write_text(
            "same123\n/System/Applications/Utilities/Terminal.app\n0\n"
        )

        with (
            patch(
                "cc_notifier.get_focused_window_id",
                return_value=("same123", "/System/Applications/Utilities/Terminal.app"),
            ),
            patch("cc_notifier.run_background_command") as mock_bg,
            patch("sys.stdin", StringIO(json.dumps(test_input))),
            patch.object(sys, "argv", ["cc-notifier", "notify"]),
            patch.object(cc_notifier, "SESSION_DIR", session_dir),
            patch("cc_notifier.PushConfig.from_env", return_value=None),
            patch.dict(os.environ, {"CC_NOTIFIER_WRAPPER": "1"}),
        ):
            cc_notifier.main()

        # Verify real end-to-end workflow behavior
        # 1. No terminal-notifier subprocess started (user stayed on same window)
        if mock_bg.called:
            bg_calls = [call[0][0] for call in mock_bg.call_args_list]
            terminal_notifier_calls = [
                cmd
                for cmd in bg_calls
                if any("terminal-notifier" in str(arg) for arg in cmd)
            ]
            assert len(terminal_notifier_calls) == 0
        # 2. Session file timestamp updated (race condition prevention)
        content = (session_dir / "notify123").read_text().strip()
        lines = content.split("\n")
        assert lines[0] == "same123"  # Window ID unchanged
        assert (
            lines[1] == "/System/Applications/Utilities/Terminal.app"
        )  # App path unchanged
        assert float(lines[2]) > 0  # Timestamp updated to prevent race conditions

    def test_notify_sent_when_same_window_but_tmux_detached(self, tmp_path):
        """Test notify sends notification when same window but tmux session is detached."""
        test_input = {"session_id": "notify123", "cwd": "/test/project"}
        session_dir = tmp_path / "cc_notifier"
        session_dir.mkdir()
        (session_dir / "notify123").write_text(
            "same123\n/System/Applications/Utilities/Terminal.app\n0\n$20"
        )

        with (
            patch(
                "cc_notifier.get_focused_window_id",
                return_value=("same123", "/System/Applications/Utilities/Terminal.app"),
            ),
            patch("cc_notifier.is_tmux_session_attached", return_value=False),
            patch("cc_notifier.run_background_command") as mock_bg,
            patch("sys.stdin", StringIO(json.dumps(test_input))),
            patch.object(sys, "argv", ["cc-notifier", "notify"]),
            patch.object(cc_notifier, "SESSION_DIR", session_dir),
            patch("cc_notifier.PushConfig.from_env", return_value=None),
            patch.dict(os.environ, {"CC_NOTIFIER_WRAPPER": "1"}),
        ):
            cc_notifier.main()

        # Notification was sent (user switched tmux sessions within same window)
        assert mock_bg.call_count >= 1
        bg_calls = [call[0][0] for call in mock_bg.call_args_list]
        terminal_notifier_calls = [
            cmd
            for cmd in bg_calls
            if any("terminal-notifier" in str(arg) for arg in cmd)
        ]
        assert len(terminal_notifier_calls) >= 1

    def test_cleanup_workflow_removes_session(self, tmp_path):
        """Test complete cleanup workflow: JSON input → real age-based file cleanup."""
        test_input = {"session_id": "cleanup123"}
        session_dir = tmp_path / "cc_notifier"
        session_dir.mkdir()

        # Create old file (6 days ago, older than 5-day threshold)
        old_file = session_dir / "old_session"
        old_file.write_text("old_data\n0")
        old_time = time.time() - (6 * 24 * 60 * 60)  # 6 days ago
        import os

        os.utime(old_file, (old_time, old_time))

        # Create new file (1 day ago, within 5-day threshold)
        new_file = session_dir / "new_session"
        new_file.write_text("new_data\n0")
        new_time = time.time() - (1 * 24 * 60 * 60)  # 1 day ago
        os.utime(new_file, (new_time, new_time))

        with (
            patch("sys.stdin", StringIO(json.dumps(test_input))),
            patch.object(sys, "argv", ["cc-notifier", "cleanup"]),
            patch.object(cc_notifier, "SESSION_DIR", session_dir),
            patch.dict(os.environ, {"CC_NOTIFIER_WRAPPER": "1"}),
        ):
            cc_notifier.main()

        # Verify real end-to-end cleanup workflow behavior
        # Age-based cleanup: old file removed, new file preserved
        assert not old_file.exists()
        assert new_file.exists()

    def test_wrapper_performance(self):
        """Test bash wrapper returns immediately, not waiting for Python script."""
        wrapper_path = Path(__file__).parent.parent / "cc-notifier"
        if not wrapper_path.exists():
            pytest.skip("Wrapper not found - run ./install.sh")

        test_json = (
            '{"session_id":"test","cwd":"/tmp","hook_event_name":"SessionStart"}'
        )

        start = time.perf_counter()
        result = subprocess.run(
            [str(wrapper_path), "init"],
            input=test_json,
            capture_output=True,
            text=True,
            timeout=2,
        )
        duration_ms = (time.perf_counter() - start) * 1000

        # Increased threshold to account for TTY capture overhead
        MAX_WRAPPER_DURATION_MS = 600.0
        print(f"\n🚀 Wrapper: {duration_ms:.1f}ms")
        assert result.returncode == 0
        assert duration_ms < MAX_WRAPPER_DURATION_MS, (
            f"Wrapper took {duration_ms:.1f}ms, expected <{MAX_WRAPPER_DURATION_MS}ms"
        )

    def test_file_locking_prevents_race_conditions(self, tmp_path):
        """Test file locking prevents race conditions between concurrent processes."""
        # Setup session file with 4-line format
        session_file = tmp_path / "test_session"
        session_file.write_text(
            "window123\n/System/Applications/Utilities/Terminal.app\n0\n$20"
        )

        # Test 1: Normal operation - should update timestamp and preserve tmux ID
        with patch("fcntl.flock") as mock_flock:
            result = cc_notifier.check_deduplication(session_file)
            assert not result  # Should proceed with notification
            assert mock_flock.called  # Lock was attempted
            # Verify timestamp was updated and tmux ID preserved
            content = session_file.read_text()
            lines = content.split("\n")
            assert lines[0] == "window123"  # Window ID unchanged
            assert (
                lines[1] == "/System/Applications/Utilities/Terminal.app"
            )  # App path unchanged
            assert float(lines[2]) > 0  # Timestamp updated
            assert lines[3] == "$20"  # tmux session ID preserved

        # Test 2: Lock contention - should skip gracefully
        session_file.write_text(
            "window123\n/System/Applications/Utilities/Terminal.app\n0\n$20"
        )  # Reset for second test
        with patch("fcntl.flock", side_effect=BlockingIOError) as mock_flock:
            old_content = session_file.read_text()
            result = cc_notifier.check_deduplication(session_file)
            assert result  # Should skip notification
            assert mock_flock.called  # Lock was attempted
            # Verify file unchanged when lock fails
            assert session_file.read_text() == old_content

    def test_push_uses_extended_intervals_when_tmux_attached_desktop(self, tmp_path):
        """Test desktop mode also uses extended idle check when tmux is attached."""
        test_input = {"session_id": "desk123", "cwd": "/test/project"}
        session_dir = tmp_path / "cc_notifier"
        session_dir.mkdir()
        (session_dir / "desk123").write_text("12345\n/app/path\n0\n$10")

        with (
            patch("cc_notifier.is_tmux_session_attached", return_value=True),
            patch(
                "cc_notifier.get_focused_window_id", return_value=("12345", "/app/path")
            ),
            patch("cc_notifier.check_idle_and_notify_push") as mock_idle_push,
            patch("cc_notifier.send_notification"),
            patch("sys.stdin", StringIO(json.dumps(test_input))),
            patch.object(sys, "argv", ["cc-notifier", "notify"]),
            patch.object(cc_notifier, "SESSION_DIR", session_dir),
            patch.dict(
                os.environ,
                {
                    "CC_NOTIFIER_WRAPPER": "1",
                    "PUSHOVER_API_TOKEN": "test_token",
                    "PUSHOVER_USER_KEY": "test_user",
                },
                clear=False,
            ),
            patch.dict(
                os.environ,
                {
                    "SSH_CONNECTION": "",
                    "SSH_CLIENT": "",
                    "SSH_TTY": "",
                },
            ),
        ):
            cc_notifier.main()

        mock_idle_push.assert_called_once()
        call_args = mock_idle_push.call_args
        intervals = call_args[0][1]
        assert intervals == cc_notifier.PUSH_IDLE_CHECK_INTERVALS_ATTACHED


class TestDataParsing:
    """Test HookData dataclass parsing and validation."""

    def test_hookdata_from_stdin_valid_json(self):
        """Test HookData.from_stdin() with valid JSON input."""
        test_json = {
            "session_id": "abc123",
            "cwd": "/Users/test/project",
            "hook_event_name": "Stop",
            "message": "Task completed",
        }

        with patch("sys.stdin", StringIO(json.dumps(test_json))):
            hook_data = cc_notifier.HookData.from_stdin()

        assert hook_data.session_id == "abc123"
        assert hook_data.cwd == "/Users/test/project"
        assert hook_data.hook_event_name == "Stop"
        assert hook_data.message == "Task completed"

    def test_hookdata_from_stdin_invalid_json_raises_error(self):
        """Test HookData.from_stdin() raises ValueError for invalid JSON."""
        with (
            patch("sys.stdin", StringIO("invalid json")),
            pytest.raises(ValueError, match="Invalid JSON input from stdin"),
        ):
            cc_notifier.HookData.from_stdin()

    def test_hookdata_filters_unexpected_fields(self):
        """Test __post_init__ removes unexpected fields correctly."""
        test_json = {
            "session_id": "abc123",
            "cwd": "/Users/test",
            "unexpected_field": "should_be_removed",
            "another_field": "also_removed",
        }

        with patch("sys.stdin", StringIO(json.dumps(test_json))):
            hook_data = cc_notifier.HookData.from_stdin()

        assert hook_data.session_id == "abc123"
        assert hook_data.cwd == "/Users/test"
        assert not hasattr(hook_data, "unexpected_field")
        assert not hasattr(hook_data, "another_field")

    def test_hookdata_defaults_applied(self):
        """Test default values are applied correctly."""
        minimal_json = {"session_id": "abc123"}

        with patch("sys.stdin", StringIO(json.dumps(minimal_json))):
            hook_data = cc_notifier.HookData.from_stdin()

        assert hook_data.session_id == "abc123"
        assert hook_data.cwd == ""
        assert hook_data.hook_event_name == "Stop"
        assert hook_data.message == ""


class TestSessionFileOperations:
    """Test session file creation, reading, and cleanup."""

    def test_save_window_id_creates_file(self):
        """Test save_window_id() creates directory and saves ID with tmux session."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_session_dir = Path(temp_dir) / "cc_notifier"

            with patch.object(cc_notifier, "SESSION_DIR", temp_session_dir):
                cc_notifier.save_window_id(
                    "test_session",
                    "12345",
                    "/System/Applications/Utilities/Terminal.app",
                    "$20",
                )

            session_file = temp_session_dir / "test_session"
            assert session_file.exists()
            assert (
                session_file.read_text()
                == "12345\n/System/Applications/Utilities/Terminal.app\n0\n$20"
            )

    def test_load_window_id_reads_saved_id(self):
        """Test load_window_id() reads saved window ID correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_session_dir = Path(temp_dir) / "cc_notifier"
            temp_session_dir.mkdir()
            session_file = temp_session_dir / "test_session"
            session_file.write_text(
                "98765\n/Applications/Visual Studio Code.app\n0\n$5"
            )

            with patch.object(cc_notifier, "SESSION_DIR", temp_session_dir):
                window_id = cc_notifier.load_window_id("test_session")

            assert window_id == "98765"

    def test_load_window_id_missing_file_raises_error(self):
        """Test load_window_id() raises FileNotFoundError when file missing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_session_dir = Path(temp_dir) / "cc_notifier"

            with (
                patch.object(cc_notifier, "SESSION_DIR", temp_session_dir),
                pytest.raises(FileNotFoundError),
            ):
                cc_notifier.load_window_id("nonexistent_session")


class TestRemoteMode:
    """Test remote session detection and remote mode behaviors."""

    def test_remote_session_detection(self):
        """Test is_remote_session() correctly detects SSH environment variables."""
        # Test with no SSH variables - desktop mode
        with patch.dict(os.environ, {}, clear=True):
            assert cc_notifier.is_remote_session() is False

        # Test with SSH_CONNECTION - remote mode
        with patch.dict(os.environ, {"SSH_CONNECTION": "1.2.3.4 12345 5.6.7.8 22"}):
            assert cc_notifier.is_remote_session() is True

        # Test with SSH_CLIENT - remote mode
        with patch.dict(os.environ, {"SSH_CLIENT": "1.2.3.4 12345 22"}):
            assert cc_notifier.is_remote_session() is True

        # Test with SSH_TTY - remote mode
        with patch.dict(os.environ, {"SSH_TTY": "/dev/pts/0"}):
            assert cc_notifier.is_remote_session() is True

    def test_remote_mode_init_uses_placeholder(self, tmp_path):
        """Test cmd_init() uses placeholder window ID in remote mode with tmux."""
        test_input = {"session_id": "remote123", "cwd": "/test/path"}
        session_dir = tmp_path / "cc_notifier"

        with (
            patch("cc_notifier.get_tmux_session_id", return_value="$10"),
            patch("sys.stdin", StringIO(json.dumps(test_input))),
            patch.object(sys, "argv", ["cc-notifier", "init"]),
            patch.object(cc_notifier, "SESSION_DIR", session_dir),
            patch.dict(
                os.environ,
                {
                    "CC_NOTIFIER_WRAPPER": "1",
                    "SSH_CONNECTION": "1.2.3.4 12345 5.6.7.8 22",
                },
            ),
        ):
            cc_notifier.main()

        # Verify placeholder window ID and tmux session ID were saved
        session_file = session_dir / "remote123"
        assert session_file.exists()
        lines = session_file.read_text().strip().split("\n")
        assert lines[0] == "REMOTE"
        assert lines[1] == "REMOTE"
        assert lines[2] == "0"
        assert lines[3] == "$10"  # tmux session ID still captured in remote mode

    def test_remote_mode_skips_local_notification(self, tmp_path):
        """Test cmd_notify() skips local notifications in remote mode."""
        test_input = {"session_id": "remote123", "cwd": "/test/project"}
        session_dir = tmp_path / "cc_notifier"
        session_dir.mkdir()
        (session_dir / "remote123").write_text("REMOTE\nREMOTE\n0\n$10")

        with (
            patch("cc_notifier.run_background_command") as mock_bg,
            patch("sys.stdin", StringIO(json.dumps(test_input))),
            patch.object(sys, "argv", ["cc-notifier", "notify"]),
            patch.object(cc_notifier, "SESSION_DIR", session_dir),
            patch.dict(
                os.environ,
                {
                    "CC_NOTIFIER_WRAPPER": "1",
                    "SSH_CONNECTION": "1.2.3.4 12345 5.6.7.8 22",
                },
            ),
        ):
            cc_notifier.main()

        # Verify no terminal-notifier subprocess started (remote mode skips local notifications)
        mock_bg.assert_not_called()

    def test_push_uses_extended_intervals_when_tmux_attached(self, tmp_path):
        """Test push uses extended idle check intervals when tmux session is attached."""
        test_input = {"session_id": "remote123", "cwd": "/test/project"}
        session_dir = tmp_path / "cc_notifier"
        session_dir.mkdir()
        (session_dir / "remote123").write_text("REMOTE\nREMOTE\n0\n$10")

        with (
            patch("cc_notifier.is_tmux_session_attached", return_value=True),
            patch("cc_notifier.check_idle_and_notify_push") as mock_idle_push,
            patch("sys.stdin", StringIO(json.dumps(test_input))),
            patch.object(sys, "argv", ["cc-notifier", "notify"]),
            patch.object(cc_notifier, "SESSION_DIR", session_dir),
            patch.dict(
                os.environ,
                {
                    "CC_NOTIFIER_WRAPPER": "1",
                    "SSH_CONNECTION": "1.2.3.4 12345 5.6.7.8 22",
                    "PUSHOVER_API_TOKEN": "test_token",
                    "PUSHOVER_USER_KEY": "test_user",
                },
            ),
        ):
            cc_notifier.main()

        # Push idle check IS called, but with extended attached intervals
        mock_idle_push.assert_called_once()
        call_args = mock_idle_push.call_args
        intervals = call_args[0][1]  # second positional arg
        assert intervals == cc_notifier.PUSH_IDLE_CHECK_INTERVALS_ATTACHED

    def test_tty_idle_detection(self):
        """Test get_tty_idle_time() correctly calculates idle time from TTY st_atime."""
        # Mock current time and TTY stat
        current_time = 1234567890
        last_read_time = current_time - 25  # 25 seconds ago

        class MockStat:
            st_atime = last_read_time

        with (
            patch("time.time", return_value=current_time),
            patch("os.stat", return_value=MockStat()),
            patch.dict(os.environ, {"CC_NOTIFIER_TTY": "/dev/pts/1"}),
        ):
            idle_time = cc_notifier.get_tty_idle_time()

        assert idle_time == 25  # Should calculate correct idle duration

    def test_baseline_idle_detection(self):
        """Test check_idle_and_notify_push() detects user activity during check period."""
        hook_data = cc_notifier.HookData(session_id="test", cwd="/test")
        push_config = cc_notifier.PushConfig(token="test_token", user="test_user")

        # Scenario: User provides input during check period
        # After waiting 3s, idle time is 2s (user typed 1s into check period)
        idle_time = 2  # User typed during our 3s check (2 < 3 = active)

        with (
            patch("cc_notifier.PushConfig.from_env", return_value=push_config),
            patch("cc_notifier.get_idle_time", return_value=idle_time),
            patch("time.sleep"),  # Skip actual sleep
            patch("cc_notifier.send_pushover_notification") as mock_send,
        ):
            cc_notifier.check_idle_and_notify_push(hook_data, [3])

        # Verify push notification was NOT sent (user was active)
        mock_send.assert_not_called()


class TestTmuxSessionDetection:
    """Test tmux session ID capture and attachment checking."""

    def test_get_tmux_session_id_success(self):
        """Test get_tmux_session_id() returns session ID when in tmux."""
        mock_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="$20\n", stderr=""
        )
        with patch("subprocess.run", return_value=mock_result):
            result = cc_notifier.get_tmux_session_id()

        assert result == "$20"

    def test_get_tmux_session_id_not_in_tmux(self):
        """Test get_tmux_session_id() returns None when not in tmux."""
        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = cc_notifier.get_tmux_session_id()

        assert result is None

    def test_get_tmux_session_id_timeout(self):
        """Test get_tmux_session_id() returns None on timeout."""
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("tmux", 2)):
            result = cc_notifier.get_tmux_session_id()

        assert result is None

    def test_is_tmux_session_attached_true(self):
        """Test is_tmux_session_attached() returns True when session has clients."""
        mock_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="2\n", stderr=""
        )
        with patch("subprocess.run", return_value=mock_result):
            result = cc_notifier.is_tmux_session_attached("$20")

        assert result is True

    def test_is_tmux_session_attached_false(self):
        """Test is_tmux_session_attached() returns False when session has no clients."""
        mock_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="0\n", stderr=""
        )
        with patch("subprocess.run", return_value=mock_result):
            result = cc_notifier.is_tmux_session_attached("$20")

        assert result is False

    def test_is_tmux_session_attached_tmux_unavailable(self):
        """Test is_tmux_session_attached() returns False when tmux is not installed."""
        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = cc_notifier.is_tmux_session_attached("$20")

        assert result is False


class TestTitleFormat:
    """Test customizable title format via CC_NOTIFIER_TITLE_FORMAT."""

    def test_default_title_when_env_not_set(self):
        """Test format_title() returns None when env var is not set."""
        hook_data = cc_notifier.HookData(session_id="test", cwd="/test/project")

        with patch.dict(os.environ, {}, clear=True):
            result = cc_notifier.format_title(hook_data)

        assert result is None

    def test_custom_format_with_dir_token(self):
        """Test {dir} token resolves to directory basename."""
        hook_data = cc_notifier.HookData(session_id="test", cwd="/Users/luke/myproject")

        with patch.dict(os.environ, {"CC_NOTIFIER_TITLE_FORMAT": "CC: {dir}"}):
            result = cc_notifier.format_title(hook_data)

        assert result == "CC: myproject"

    def test_custom_format_with_hostname_token(self):
        """Test {hostname} token resolves to socket.gethostname()."""
        hook_data = cc_notifier.HookData(session_id="test", cwd="/test")

        with (
            patch.dict(os.environ, {"CC_NOTIFIER_TITLE_FORMAT": "{hostname}"}),
            patch("socket.gethostname", return_value="lukes-mbp"),
        ):
            result = cc_notifier.format_title(hook_data)

        assert result == "lukes-mbp"

    def test_custom_format_with_tmux_session_token(self):
        """Test {tmux_session} token resolves via tmux command."""
        hook_data = cc_notifier.HookData(session_id="test", cwd="/test")

        mock_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="dev-session\n", stderr=""
        )
        with (
            patch.dict(os.environ, {"CC_NOTIFIER_TITLE_FORMAT": "{tmux_session}"}),
            patch("subprocess.run", return_value=mock_result),
        ):
            result = cc_notifier.format_title(hook_data)

        assert result == "dev-session"

    def test_tmux_session_empty_when_not_in_tmux(self):
        """Test {tmux_session} resolves to empty string when tmux is not available."""
        hook_data = cc_notifier.HookData(session_id="test", cwd="/test")

        with (
            patch.dict(os.environ, {"CC_NOTIFIER_TITLE_FORMAT": "X{tmux_session}X"}),
            patch("subprocess.run", side_effect=FileNotFoundError),
        ):
            result = cc_notifier.format_title(hook_data)

        assert result == "XX"

    def test_custom_format_with_cwd_token(self):
        """Test {cwd} token resolves to full working directory."""
        hook_data = cc_notifier.HookData(
            session_id="test", cwd="/Users/luke/code/project"
        )

        with patch.dict(os.environ, {"CC_NOTIFIER_TITLE_FORMAT": "{cwd}"}):
            result = cc_notifier.format_title(hook_data)

        assert result == "/Users/luke/code/project"

    def test_custom_format_with_all_tokens(self):
        """Test format string with all built-in tokens."""
        hook_data = cc_notifier.HookData(session_id="test", cwd="/Users/luke/myproject")

        mock_tmux = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="main\n", stderr=""
        )
        with (
            patch.dict(
                os.environ,
                {"CC_NOTIFIER_TITLE_FORMAT": "{hostname} · {tmux_session} · {dir}"},
            ),
            patch("socket.gethostname", return_value="ec2-dev"),
            patch("subprocess.run", return_value=mock_tmux),
        ):
            result = cc_notifier.format_title(hook_data)

        assert result == "ec2-dev · main · myproject"

    def test_env_var_token(self):
        """Test {env:VAR_NAME} resolves to environment variable value."""
        hook_data = cc_notifier.HookData(session_id="test", cwd="/test")

        with patch.dict(
            os.environ,
            {
                "CC_NOTIFIER_TITLE_FORMAT": "{env:MY_CUSTOM_LABEL}",
                "MY_CUSTOM_LABEL": "custom-host",
            },
        ):
            result = cc_notifier.format_title(hook_data)

        assert result == "custom-host"

    def test_env_var_token_missing_var(self):
        """Test {env:VAR_NAME} resolves to empty string when var is not set."""
        hook_data = cc_notifier.HookData(session_id="test", cwd="/test")

        env = {"CC_NOTIFIER_TITLE_FORMAT": "X{env:NONEXISTENT_VAR}X"}
        with patch.dict(os.environ, env, clear=True):
            result = cc_notifier.format_title(hook_data)

        assert result == "XX"

    def test_env_var_token_mixed_with_builtins(self):
        """Test {env:VAR} mixed with built-in tokens."""
        hook_data = cc_notifier.HookData(session_id="test", cwd="/test/proj")

        with patch.dict(
            os.environ,
            {
                "CC_NOTIFIER_TITLE_FORMAT": "{env:TEAM} - {dir}",
                "TEAM": "infra",
            },
        ):
            result = cc_notifier.format_title(hook_data)

        assert result == "infra - proj"

    def test_resolve_title_tokens_returns_all_keys(self):
        """Test resolve_title_tokens returns all keys when template uses them all."""
        hook_data = cc_notifier.HookData(session_id="test", cwd="/test/project")
        template = "{hostname} {tmux_session} {dir} {cwd}"

        mock_tmux = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="sess\n", stderr=""
        )
        with (
            patch("socket.gethostname", return_value="myhost"),
            patch("subprocess.run", return_value=mock_tmux),
        ):
            tokens = cc_notifier.resolve_title_tokens(hook_data, template)

        assert set(tokens.keys()) == {"hostname", "tmux_session", "dir", "cwd"}
        assert tokens["hostname"] == "myhost"
        assert tokens["tmux_session"] == "sess"
        assert tokens["dir"] == "project"
        assert tokens["cwd"] == "/test/project"

    def test_resolve_title_tokens_skips_tmux_when_not_in_template(self):
        """Test that tmux subprocess is not called when {tmux_session} is not in template."""
        hook_data = cc_notifier.HookData(session_id="test", cwd="/test/project")
        template = "{hostname} {dir}"

        with (
            patch("socket.gethostname", return_value="myhost"),
            patch("subprocess.run") as mock_run,
        ):
            tokens = cc_notifier.resolve_title_tokens(hook_data, template)

        mock_run.assert_not_called()
        assert "tmux_session" not in tokens
        assert tokens["hostname"] == "myhost"

    def test_create_notification_data_uses_format_title(self):
        """Test create_notification_data uses format_title for both local and push."""
        hook_data = cc_notifier.HookData(session_id="test", cwd="/test/project")

        with (
            patch.dict(os.environ, {"CC_NOTIFIER_TITLE_FORMAT": "{dir} on {hostname}"}),
            patch("socket.gethostname", return_value="myhost"),
        ):
            local_title, _, _ = cc_notifier.create_notification_data(
                hook_data, for_push=False
            )
            push_title, _, _ = cc_notifier.create_notification_data(
                hook_data, for_push=True
            )

        assert local_title == "project on myhost"
        assert push_title == "project on myhost"

    def test_create_notification_data_default_preserves_originals(self):
        """Test default titles: local gets 'Claude Code 🔔', push gets project basename."""
        hook_data = cc_notifier.HookData(session_id="test", cwd="/test/project")

        with patch.dict(os.environ, {}, clear=True):
            local_title, _, _ = cc_notifier.create_notification_data(
                hook_data, for_push=False
            )
            push_title, _, _ = cc_notifier.create_notification_data(
                hook_data, for_push=True
            )

        assert local_title == "Claude Code 🔔"
        assert push_title == "project"


class TestPushNotificationURL:
    """Test push notification URL construction and encoding."""

    def test_build_push_url_substitutes_placeholders(self):
        """Test build_push_url() substitutes {cwd} and {session_id} placeholders."""
        hook_data = cc_notifier.HookData(session_id="abc123", cwd="/Users/test/project")
        url_template = "blinkshell://run?key=531915&cmd=cd {cwd} && ls"

        with patch.dict(os.environ, {"CC_NOTIFIER_PUSH_URL": url_template}):
            result = cc_notifier.build_push_url(hook_data)

        expected = "blinkshell://run?key=531915&cmd=cd /Users/test/project && ls"
        assert result == expected

    def test_build_push_url_preserves_query_parameters(self):
        """Test query parameters (?, &, =) are preserved in custom URL schemes."""
        hook_data = cc_notifier.HookData(session_id="xyz789", cwd="/home/user/work")
        url_template = "myapp://action?session={session_id}&path={cwd}&flag=true"

        with patch.dict(os.environ, {"CC_NOTIFIER_PUSH_URL": url_template}):
            result = cc_notifier.build_push_url(hook_data)

        expected = "myapp://action?session=xyz789&path=/home/user/work&flag=true"
        assert result == expected
        # Verify all query parameter characters preserved
        assert "?" in result
        assert "&" in result
        assert "=" in result

    def test_build_push_url_returns_none_when_not_configured(self):
        """Test build_push_url() returns None when CC_NOTIFIER_PUSH_URL not set."""
        hook_data = cc_notifier.HookData(session_id="test123", cwd="/test/path")

        with patch.dict(os.environ, {}, clear=True):
            result = cc_notifier.build_push_url(hook_data)

        assert result is None

    def test_build_push_url_with_special_characters_in_path(self):
        """Test URL construction with special characters in cwd path."""
        hook_data = cc_notifier.HookData(
            session_id="test123", cwd="/Users/orlando/My Projects/app-v2.0"
        )
        url_template = "blinkshell://run?cmd=cd {cwd}"

        with patch.dict(os.environ, {"CC_NOTIFIER_PUSH_URL": url_template}):
            result = cc_notifier.build_push_url(hook_data)

        expected = "blinkshell://run?cmd=cd /Users/orlando/My Projects/app-v2.0"
        assert result == expected
        # Note: Spaces are user's responsibility to handle in their command/script

    def test_push_url_survives_urlencode(self):
        """Test that custom URL schemes survive urllib.parse.urlencode() for POST body."""
        hook_data = cc_notifier.HookData(session_id="test123", cwd="/home/user/project")
        url_template = (
            "blinkshell://run?key=531915&cmd=mosh mbp -- ~/bin/start.sh {cwd}"
        )

        with patch.dict(os.environ, {"CC_NOTIFIER_PUSH_URL": url_template}):
            push_url = cc_notifier.build_push_url(hook_data)

        # Simulate what send_pushover_notification does
        import urllib.parse

        data_dict = {
            "token": "test_token",
            "user": "test_user",
            "title": "Test",
            "message": "Test message",
            "url": push_url,
        }
        encoded_data = urllib.parse.urlencode(data_dict)

        # Verify URL is present in encoded POST body
        assert "url=" in encoded_data
        assert "blinkshell" in encoded_data

        # Decode and verify URL survived encoding/decoding
        decoded = urllib.parse.parse_qs(encoded_data)
        recovered_url = decoded["url"][0]

        expected_url = (
            "blinkshell://run?key=531915&cmd=mosh mbp -- ~/bin/start.sh "
            "/home/user/project"
        )
        assert recovered_url == expected_url
        # Verify critical URL components survived
        assert "blinkshell://" in recovered_url
        assert "key=531915" in recovered_url
        assert "cmd=mosh" in recovered_url
        assert "/home/user/project" in recovered_url
