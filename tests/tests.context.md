# Test Context

Associated with: all tests in the codebase

**OVERVIEW**: This document provides a comprehensive reference for all tests in the codebase, detailing their purpose, scope, and quality. It serves as a guide for understanding the testing strategy and ensuring that tests remain aligned with project goals.

**IMPORTANT**: This file must be kept current with all tests in the codebase. Update when tests are added, removed, or modified.

**Format**: `test_name` - [concise description of what's being tested] - [rationale for why test is needed]

**Status**: **28 total tests** across 2 files - All tests properly accounted for and documented

**Structure**: Tests are organized by functionality and concerns, emphasizing behavior-focused testing over implementation details. The 2-file structure matches the natural architectural boundary between core logic and external system integration.

---

## test_core.py (22 tests) - Core Functionality & Essential Business Logic

### TestCLIInterface (8 tests) - Essential CLI Contract Testing
- `test_main_with_no_args_exits_with_error` - CLI error handling when no command provided - CLI must provide helpful usage info and exit gracefully
- `test_main_with_invalid_command_exits_with_error` - CLI error handling for unknown commands - Prevents silent failures and provides user guidance
- `test_main_version_flag_shows_version` - Version display functionality with --version and -v flags - Essential for troubleshooting and system compatibility
- `test_main_exception_handling_exits_with_status_1` - Main function exception handling and proper exit codes - Critical for Claude Code hook integration and error detection
- `test_debug_flag_parsing` - Debug flag detection, removal from argv, and state setting - Tests actual main() function behavior with debug flag
- `test_main_exception_logged_and_exits_1` - Main function error logging and exit code 1 - Essential for Claude Code hook error detection and debugging
- `test_main_blocks_direct_execution_without_wrapper_env` - Prevents direct execution without wrapper environment variable - Critical for preventing Claude Code hooks from blocking
- `test_main_allows_execution_with_wrapper_env` - Allows execution when wrapper environment variable is set - Ensures proper wrapper integration works correctly

### TestCoreWorkflows (7 tests) - End-to-End Workflow Validation
- `test_init_workflow_captures_and_saves_window` - Complete init workflow from JSON input to file creation - End-to-end validation of session initialization
- `test_notify_workflow_user_switched_sends_notification` - Complete notify workflow when user switched windows - End-to-end validation of notification sending
- `test_notify_workflow_user_stayed_no_notification` - Complete notify workflow when user stayed on same window - End-to-end validation of intelligent notification suppression
- `test_cleanup_workflow_removes_session` - Complete cleanup workflow with age-based file removal - End-to-end validation of session cleanup functionality
- `test_main_cleanup_command_routing` - Real cleanup command execution with age-based file removal - Ensures cleanup actually works with real file operations
- `test_wrapper_performance` - Bash wrapper returns immediately without waiting for Python - Critical for non-blocking hook execution in Claude Code
- `test_file_locking_prevents_race_conditions` - File locking prevents race conditions between concurrent notify processes - Essential for preventing duplicate notifications in high-frequency scenarios

### TestDataParsing (4 tests) - Hook Data Contract Testing
- `test_hookdata_from_stdin_valid_json` - JSON input parsing from Claude Code hooks - Core functionality for receiving hook data
- `test_hookdata_from_stdin_invalid_json_raises_error` - Malformed JSON input error handling - Prevents silent failures when Claude Code sends bad data
- `test_hookdata_filters_unexpected_fields` - Filtering unknown fields from hook data - Maintains compatibility when Claude Code adds new fields
- `test_hookdata_defaults_applied` - Default values for missing optional fields - Ensures predictable behavior with minimal hook data

### TestSessionFileOperations (3 tests) - Session Persistence Testing
- `test_save_window_id_creates_file` - Session file creation with window ID and timestamp - Essential for window focus restoration functionality
- `test_load_window_id_reads_saved_id` - Session file reading and window ID extraction - Required for determining original window to focus
- `test_load_window_id_missing_file_raises_error` - Error handling when session file doesn't exist - Prevents undefined behavior when files are missing

---

## test_integrations.py (6 tests) - External System Boundaries & Integration Testing

### TestHammerspoonIntegration (1 test) - Consolidated External System Testing
- `test_hammerspoon_cli_integration` - Hammerspoon CLI success, timeout, error scenarios, and focus command generation - Comprehensive testing of window management integration in a single consolidated test

### TestExternalSystemErrorHandling (2 tests) - System Boundary Error Testing
- `test_json_parsing_error_recovery` - Error handling for malformed JSON from Claude Code hooks - Prevents undefined behavior with bad hook data
- `test_corrupted_session_file_handling` - Error handling for corrupted/unreadable session files - Prevents undefined behavior with bad file data

### TestNotificationSystemIntegration (3 tests) - Notification Boundary Testing
- `test_create_focus_command_generates_correct_script` - Focus command generation for window restoration - Essential for click-to-focus functionality
- `test_terminal_notifier_command_construction` - Command construction for notification scenarios and focus parameters - Validates command-line argument generation and click-to-focus integration
- `test_basic_error_logging_functionality` - Basic error logging to file with error details - Essential for troubleshooting issues in production