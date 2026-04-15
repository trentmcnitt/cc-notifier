"""
System integration tests for cc-notifier.

Tests external system interactions including Hammerspoon CLI, terminal-notifier,
error handling, and notification system integration. Focuses on system boundary
interactions and external dependency contracts.
"""

import os
import subprocess
import sys
from io import StringIO
from unittest.mock import patch

import pytest

import cc_notifier


class TestHammerspoonIntegration:
    """Test Hammerspoon CLI integration for window management."""

    @patch("cc_notifier.run_command")
    def test_hammerspoon_cli_integration(self, mock_run_command):
        """Test Hammerspoon CLI integration with success, timeout, and error scenarios."""
        # Test 1: Success scenario
        mock_run_command.return_value = (
            "98765|/System/Applications/Utilities/Terminal.app"
        )
        window_id, app_path = cc_notifier.get_focused_window_id()
        assert window_id == "98765"
        assert app_path == "/System/Applications/Utilities/Terminal.app"

        # Verify command construction
        args = mock_run_command.call_args[0][0]
        assert str(cc_notifier.HAMMERSPOON_CLI) in args
        assert "-c" in args

        # Test 2: Timeout handling
        mock_run_command.reset_mock()
        mock_run_command.side_effect = subprocess.TimeoutExpired("hs", 10)

        with pytest.raises(RuntimeError, match="timed out"):
            cc_notifier.get_focused_window_id()

        # Test 3: ERROR response handling
        mock_run_command.reset_mock()
        mock_run_command.side_effect = None
        mock_run_command.return_value = "ERROR"

        with pytest.raises(RuntimeError, match="Failed to get focused window ID"):
            cc_notifier.get_focused_window_id()


class TestExternalSystemErrorHandling:
    """Test error handling for external system interactions."""

    def test_json_parsing_error_recovery(self, tmp_path):
        """Test error handling for malformed JSON from Claude Code hooks."""
        session_dir = tmp_path / "cc_notifier"

        # Test with completely invalid JSON
        with (
            patch("sys.stdin", StringIO("not valid json at all")),
            patch.object(sys, "argv", ["cc-notifier", "init"]),
            patch.object(cc_notifier, "SESSION_DIR", session_dir),
            patch.dict(os.environ, {"CC_NOTIFIER_WRAPPER": "1"}),
            patch("cc_notifier.run_background_command"),
        ):
            try:
                cc_notifier.main()
                raise AssertionError("Should have raised SystemExit due to JSON error")
            except SystemExit as e:
                assert e.code == 1

        # Test with valid JSON but missing required fields
        with (
            patch("sys.stdin", StringIO('{"invalid": "missing session_id"}')),
            patch.object(sys, "argv", ["cc-notifier", "init"]),
            patch.object(cc_notifier, "SESSION_DIR", session_dir),
            patch.dict(os.environ, {"CC_NOTIFIER_WRAPPER": "1"}),
            patch("cc_notifier.run_background_command"),
        ):
            try:
                cc_notifier.main()
                raise AssertionError(
                    "Should have raised SystemExit due to missing session_id"
                )
            except SystemExit as e:
                assert e.code == 1

    def test_corrupted_session_file_handling(self, tmp_path):
        """Test handling corrupted session files."""
        session_dir = tmp_path / "cc_notifier"
        session_dir.mkdir()
        (session_dir / "test").write_bytes(b"\xff\xfe")

        with (
            patch.object(cc_notifier, "SESSION_DIR", session_dir),
            pytest.raises(UnicodeDecodeError),
        ):
            cc_notifier.load_window_id("test")


class TestNotificationSystemIntegration:
    """Test notification system integration and command construction."""

    def test_create_focus_command_generates_correct_script(self):
        """Test create_focus_command() generates correct Hammerspoon script."""
        window_id = "12345"
        command = cc_notifier.create_focus_command(window_id)

        assert len(command) == 3
        assert str(cc_notifier.HAMMERSPOON_CLI) == command[0]
        assert command[1] == "-c"
        assert "12345" in command[2]
        assert "w:focus()" in command[2]
        assert "hs.window.filter" in command[2]

    def test_create_focus_command_includes_iterm2_tab_restore(self):
        """Test create_focus_command() includes iTerm2 tab restore when session ID provided."""
        command = cc_notifier.create_focus_command("12345", "w0t1p0")

        assert len(command) == 3
        assert command[0] == "/bin/sh"
        assert command[1] == "-c"
        assert "hs.window.filter" in command[2]
        assert "osascript" in command[2]
        assert "w0t1p0" in command[2]

    @patch("subprocess.Popen")
    def test_terminal_notifier_command_construction(self, mock_popen):
        """Test proper command construction for notification scenarios."""
        # Test basic notification command construction
        cc_notifier.send_notification(
            title="Test Title", subtitle="Test Subtitle", message="Test Message"
        )

        mock_popen.assert_called_once()
        cmd = mock_popen.call_args[0][0]

        # Verify complete command structure
        expected_basic_cmd = [
            cc_notifier.TERMINAL_NOTIFIER,
            "-title",
            "Test Title",
            "-subtitle",
            "Test Subtitle",
            "-message",
            "Test Message",
            "-sound",
            "Glass",
            "-ignoreDnD",
        ]
        assert cmd == expected_basic_cmd

        # Test command with focus parameter (execute parameter)
        mock_popen.reset_mock()
        window_id = "98765"
        cc_notifier.send_notification(
            title="Focus Test",
            subtitle="Test Subtitle",
            message="Test Message",
            focus_window_id=window_id,
        )

        cmd = mock_popen.call_args[0][0]

        # Verify execute parameter is included
        assert "-execute" in cmd
        execute_index = cmd.index("-execute")
        execute_command = cmd[execute_index + 1]

        # Verify the execute command contains the window ID and focus logic
        assert window_id in execute_command
        assert "w:id()==98765" in execute_command
        assert "w:focus()" in execute_command
        assert "hs.window.filter" in execute_command

    def test_basic_error_logging_functionality(self, tmp_path):
        """Test basic error logging functionality."""
        log_file = tmp_path / ".cc-notifier" / "cc-notifier.log"

        with patch.object(cc_notifier, "LOG_FILE", log_file):
            cc_notifier.log_error("Test error", ValueError("test"))

            assert log_file.exists()
            content = log_file.read_text()
            assert "Test error" in content
            assert "ValueError: test" in content


class TestITerm2Integration:
    """Test iTerm2 detection and session capture helpers."""

    def test_is_iterm2_app_detection(self):
        """Test iTerm2 app path detection for iTerm and iTerm2 variants."""
        assert cc_notifier.is_iterm2_app("/Applications/iTerm.app")
        assert cc_notifier.is_iterm2_app("/Applications/iTerm2.app")
        assert not cc_notifier.is_iterm2_app(
            "/System/Applications/Utilities/Terminal.app"
        )

    @patch("cc_notifier.run_command")
    def test_get_iterm2_focused_session_id(self, mock_run_command):
        """Test iTerm2 focused session ID capture and fallback behavior."""
        mock_run_command.return_value = "w0t0p0"
        assert cc_notifier.get_iterm2_focused_session_id() == "w0t0p0"

        mock_run_command.side_effect = RuntimeError("osascript failed")
        assert cc_notifier.get_iterm2_focused_session_id() == ""
