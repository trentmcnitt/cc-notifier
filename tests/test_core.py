"""
Core functionality tests for cc-notifier.

Tests CLI interface, core workflows, data parsing, and session file operations.
Focuses on essential user-facing behaviors that must work reliably.
"""

import json
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
        ):
            cc_notifier.main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Usage:" in captured.out

    def test_main_version_flag_shows_version(self, capsys):
        """Test --version and -v flags return correct version."""
        for flag in ["--version", "-v"]:
            with patch.object(sys, "argv", ["cc-notifier", flag]):
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
            pytest.raises(SystemExit) as exc_info,
        ):
            cc_notifier.main()

        assert exc_info.value.code == 1

        # Verify real log file was created with error content
        assert log_file.exists()
        content = log_file.read_text()
        assert "Command 'notify' failed" in content
        assert "ValueError: Test error" in content


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
