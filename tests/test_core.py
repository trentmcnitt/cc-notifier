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
            patch(
                "cc_notifier.HookData.from_stdin", side_effect=ValueError("Test error")
            ),
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
                patch("cc_notifier.save_window_id") as mock_save,
                patch.dict(os.environ, {"CC_NOTIFIER_WRAPPER": "1"}),
            ):
                # Setup mocks to allow init to complete
                mock_stdin.return_value = cc_notifier.HookData(session_id="test")
                mock_window.return_value = "12345"

                # Test actual main() call with debug flag
                cc_notifier.main()

                # Verify debug flag was processed and enabled logging
                assert cc_notifier.DEBUG is True

                # Verify the underlying command executed (init was called)
                mock_stdin.assert_called_once()
                mock_window.assert_called_once()
                mock_save.assert_called_once_with("test", "12345")

        finally:
            # Restore original state
            cc_notifier.DEBUG = original_debug

    def test_main_exception_logged_and_exits_1(self, tmp_path):
        """Test main() logs real command errors and exits with status 1."""
        log_file = tmp_path / ".cc-notifier" / "cc-notifier.log"
        session_dir = tmp_path / "cc_notifier"
        session_dir.mkdir()
        (session_dir / "test").write_text("12345\n0")

        with (
            patch.object(cc_notifier, "LOG_FILE", log_file),
            patch.object(cc_notifier, "SESSION_DIR", session_dir),
            patch("sys.argv", ["cc-notifier", "notify"]),
            patch("sys.stdin.read", return_value='{"session_id": "test"}'),
            patch(
                "cc_notifier.get_focused_window_id",
                side_effect=ValueError("Test error"),
            ),
            patch.dict(os.environ, {"CC_NOTIFIER_WRAPPER": "1"}),
            pytest.raises(SystemExit) as exc_info,
        ):
            cc_notifier.main()

        assert exc_info.value.code == 1

        # Verify real log file was created with error content
        assert log_file.exists()
        content = log_file.read_text()
        assert "Command 'notify' failed" in content
        assert "ValueError: Test error" in content

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
            patch("cc_notifier.get_focused_window_id", return_value="54321"),
            patch("sys.stdin", StringIO(json.dumps(test_input))),
            patch.object(sys, "argv", ["cc-notifier", "init"]),
            patch.object(cc_notifier, "SESSION_DIR", session_dir),
            patch.dict(os.environ, {"CC_NOTIFIER_WRAPPER": "1"}),
        ):
            cc_notifier.main()

        # Verify real end-to-end workflow behavior
        session_file = session_dir / "workflow123"
        assert session_file.exists()
        content = session_file.read_text().strip()
        assert content == "54321\n0"  # window_id + initial timestamp

    def test_notify_workflow_user_switched_sends_notification(self, tmp_path):
        """Test notify workflow when user switched: JSON input → file read → real notification."""
        test_input = {"session_id": "notify123", "cwd": "/test/project"}
        # Create session file with new format (window_id + old timestamp)
        session_dir = tmp_path / "cc_notifier"
        session_dir.mkdir()
        (session_dir / "notify123").write_text("original123\n0")

        with (
            patch("cc_notifier.get_focused_window_id", return_value="different456"),
            patch("subprocess.Popen") as mock_popen,
            patch("sys.stdin", StringIO(json.dumps(test_input))),
            patch.object(sys, "argv", ["cc-notifier", "notify"]),
            patch.object(cc_notifier, "SESSION_DIR", session_dir),
            patch("cc_notifier.check_idle_and_notify_push"),  # Mock push notifications
            patch.dict(os.environ, {"CC_NOTIFIER_WRAPPER": "1"}),
        ):
            cc_notifier.main()

        # Verify real end-to-end workflow behavior
        # 1. Notification subprocess was started
        assert mock_popen.call_count >= 1
        # 2. Verify terminal-notifier command was called
        popen_calls = [call[0][0] for call in mock_popen.call_args_list]
        terminal_notifier_calls = [
            cmd
            for cmd in popen_calls
            if any("terminal-notifier" in str(arg) for arg in cmd)
        ]
        assert len(terminal_notifier_calls) >= 1
        # 3. Session file timestamp was updated
        content = (session_dir / "notify123").read_text().strip()
        window_id, timestamp = content.split("\n")
        assert window_id == "original123"  # Window ID unchanged
        assert float(timestamp) > 0  # Timestamp updated

    def test_notify_workflow_user_stayed_no_notification(self, tmp_path):
        """Test notify workflow when user stayed: JSON input → file read → no notification."""
        test_input = {"session_id": "notify123"}
        # Create session file with new format (window_id + old timestamp)
        session_dir = tmp_path / "cc_notifier"
        session_dir.mkdir()
        (session_dir / "notify123").write_text("same123\n0")

        with (
            patch("cc_notifier.get_focused_window_id", return_value="same123"),
            patch("subprocess.Popen") as mock_popen,
            patch("sys.stdin", StringIO(json.dumps(test_input))),
            patch.object(sys, "argv", ["cc-notifier", "notify"]),
            patch.object(cc_notifier, "SESSION_DIR", session_dir),
            patch("cc_notifier.check_idle_and_notify_push"),  # Mock push notifications
            patch.dict(os.environ, {"CC_NOTIFIER_WRAPPER": "1"}),
        ):
            cc_notifier.main()

        # Verify real end-to-end workflow behavior
        # 1. No terminal-notifier subprocess started (user stayed on same window)
        if mock_popen.called:
            popen_calls = [call[0][0] for call in mock_popen.call_args_list]
            terminal_notifier_calls = [
                cmd
                for cmd in popen_calls
                if any("terminal-notifier" in str(arg) for arg in cmd)
            ]
            assert len(terminal_notifier_calls) == 0
        # 2. Session file timestamp updated (race condition prevention)
        content = (session_dir / "notify123").read_text().strip()
        lines = content.split("\n")
        assert lines[0] == "same123"  # Window ID unchanged
        assert float(lines[1]) > 0  # Timestamp updated to prevent race conditions

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

    def test_main_cleanup_command_routing(self, tmp_path):
        """Test that cleanup command performs real age-based cleanup."""
        # Create temporary session directory with old and new files
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

        test_input = {"session_id": "test123"}
        with (
            patch("sys.stdin", StringIO(json.dumps(test_input))),
            patch.object(sys, "argv", ["cc-notifier", "cleanup"]),
            patch.object(cc_notifier, "SESSION_DIR", session_dir),
            patch.dict(os.environ, {"CC_NOTIFIER_WRAPPER": "1"}),
        ):
            cc_notifier.main()

        # Verify age-based cleanup worked: old file removed, new file preserved
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

        MAX_WRAPPER_DURATION_MS = 15.0
        print(f"\n🚀 Wrapper: {duration_ms:.1f}ms")
        assert result.returncode == 0
        assert duration_ms < MAX_WRAPPER_DURATION_MS, (
            f"Wrapper took {duration_ms:.1f}ms, expected <{MAX_WRAPPER_DURATION_MS}ms"
        )

    def test_file_locking_prevents_race_conditions(self, tmp_path):
        """Test file locking prevents race conditions between concurrent processes."""
        # Setup session file with old timestamp
        session_file = tmp_path / "test_session"
        session_file.write_text("window123\n0")

        # Test 1: Normal operation - should update timestamp and proceed
        with patch("fcntl.flock") as mock_flock:
            result = cc_notifier.check_deduplication(session_file)
            assert not result  # Should proceed with notification
            assert mock_flock.called  # Lock was attempted
            # Verify timestamp was updated atomically
            content = session_file.read_text()
            lines = content.split("\n")
            assert lines[0] == "window123"  # Window ID unchanged
            assert float(lines[1]) > 0  # Timestamp updated

        # Test 2: Lock contention - should skip gracefully
        session_file.write_text("window123\n0")  # Reset for second test
        with patch("fcntl.flock", side_effect=BlockingIOError) as mock_flock:
            old_content = session_file.read_text()
            result = cc_notifier.check_deduplication(session_file)
            assert result  # Should skip notification
            assert mock_flock.called  # Lock was attempted
            # Verify file unchanged when lock fails
            assert session_file.read_text() == old_content


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
        """Test save_window_id() creates directory and saves ID."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_session_dir = Path(temp_dir) / "cc_notifier"

            with patch.object(cc_notifier, "SESSION_DIR", temp_session_dir):
                cc_notifier.save_window_id("test_session", "12345")

            session_file = temp_session_dir / "test_session"
            assert session_file.exists()
            assert session_file.read_text() == "12345\n0"

    def test_load_window_id_reads_saved_id(self):
        """Test load_window_id() reads saved window ID correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_session_dir = Path(temp_dir) / "cc_notifier"
            temp_session_dir.mkdir()
            session_file = temp_session_dir / "test_session"
            session_file.write_text("98765\n0")

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
        """Test cmd_init() uses placeholder window ID in remote mode."""
        test_input = {"session_id": "remote123", "cwd": "/test/path"}
        session_dir = tmp_path / "cc_notifier"

        with (
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

        # Verify placeholder window ID was saved
        session_file = session_dir / "remote123"
        assert session_file.exists()
        content = session_file.read_text().strip()
        assert content == "REMOTE\n0"

    def test_remote_mode_skips_local_notification(self, tmp_path):
        """Test cmd_notify() skips local notifications in remote mode."""
        test_input = {"session_id": "remote123", "cwd": "/test/project"}
        session_dir = tmp_path / "cc_notifier"
        session_dir.mkdir()
        (session_dir / "remote123").write_text("REMOTE\n0")

        with (
            patch("subprocess.Popen") as mock_popen,
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
        if mock_popen.called:
            popen_calls = [call[0][0] for call in mock_popen.call_args_list]
            terminal_notifier_calls = [
                cmd
                for cmd in popen_calls
                if any("terminal-notifier" in str(arg) for arg in cmd)
            ]
            assert len(terminal_notifier_calls) == 0

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
        ):
            idle_time = cc_notifier.get_tty_idle_time()

        assert idle_time == 25  # Should calculate correct idle duration

    def test_baseline_idle_detection(self):
        """Test check_idle_and_notify_push() uses baseline comparison to detect user input."""
        hook_data = cc_notifier.HookData(session_id="test", cwd="/test")
        push_config = cc_notifier.PushConfig(token="test_token", user="test_user")

        # Scenario: User was idle for 30 seconds when hook triggered,
        # then provided input after 2 seconds (idle time reset to 0)
        baseline_idle = 30  # User idle for 30 seconds when hook triggered
        idle_after_2s = 2  # After 2s delay, user is idle for only 2s (provided input!)

        call_count = 0

        def mock_get_idle_time():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return baseline_idle  # Initial baseline capture
            return idle_after_2s  # User provided input (idle time decreased)

        with (
            patch("cc_notifier.PushConfig.from_env", return_value=push_config),
            patch("cc_notifier.get_idle_time", side_effect=mock_get_idle_time),
            patch("time.sleep"),  # Skip actual sleep
            patch("cc_notifier.send_pushover_notification") as mock_send,
        ):
            cc_notifier.check_idle_and_notify_push(hook_data, [3])

        # Verify push notification was NOT sent (user provided input)
        mock_send.assert_not_called()
