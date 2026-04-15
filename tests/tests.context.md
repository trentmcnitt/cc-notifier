# Test Context

Associated with: all tests in the codebase

**OVERVIEW**: This document provides a comprehensive reference for all tests in the codebase, detailing their purpose, scope, and quality. It serves as a guide for understanding the testing strategy and ensuring that tests remain aligned with project goals.

**IMPORTANT**: This file must be kept current with all tests in the codebase. Update when tests are added, removed, or modified.

**Format**: `test_name` - [concise description of what's being tested] - [rationale for why test is needed]

**Status**: **71 total tests** (62 core + 9 integration) across 2 files - All tests properly accounted for and documented

**Structure**: Tests are organized by functionality and concerns, emphasizing behavior-focused testing over implementation details. The 2-file structure matches the natural architectural boundary between core logic and external system integration.

---

## test_core.py (62 tests) - Core Functionality & Essential Business Logic

### TestCLIInterface (9 tests) - Essential CLI Contract Testing
- `test_main_with_no_args_exits_with_error` - CLI error handling when no command provided - CLI must provide helpful usage info and exit gracefully
- `test_main_with_invalid_command_exits_with_error` - CLI error handling for unknown commands - Prevents silent failures and provides user guidance
- `test_main_version_flag_shows_version` - Version display functionality with --version and -v flags - Essential for troubleshooting and system compatibility
- `test_main_exception_handling_exits_with_status_1` - Main function exception handling and proper exit codes - Critical for Claude Code hook integration and error detection
- `test_debug_flag_parsing` - Debug flag detection, removal from argv, and state setting - Tests actual main() function behavior with debug flag
- `test_main_exception_logged_and_exits_1` - Main function error logging and exit code 1 - Essential for Claude Code hook error detection and debugging
- `test_notify_continues_to_push_when_local_fails` - Notify gracefully handles local notification failure and continues to push - Essential for resilient notification delivery
- `test_main_blocks_direct_execution_without_wrapper_env` - Prevents direct execution without wrapper environment variable - Critical for preventing Claude Code hooks from blocking
- `test_main_allows_execution_with_wrapper_env` - Allows execution when wrapper environment variable is set - Ensures proper wrapper integration works correctly

### TestCoreWorkflows (15 tests) - End-to-End Workflow Validation
- `test_init_workflow_captures_and_saves_window` - Complete init workflow from JSON input to file creation including tmux session ID - End-to-end validation of session initialization
- `test_init_workflow_without_hammerspoon` - Init falls back to UNAVAILABLE but still captures tmux session ID - Validates graceful degradation
- `test_init_workflow_captures_iterm2_session_id` - Init captures iTerm2 focused session ID alongside window metadata - Enables same-window tab restoration for iTerm2
- `test_notify_suppressed_when_tmux_attached_without_hammerspoon` - Notify suppresses local notification when tmux session is attached - Prevents false positives in tmux
- `test_notify_sent_when_tmux_detached_without_hammerspoon` - Notify sends local notification when tmux session is detached - Ensures notifications when user truly away
- `test_notify_sent_without_hammerspoon_or_tmux` - Notify sends unconditionally when neither Hammerspoon nor tmux available - Fallback behavior
- `test_notify_workflow_user_switched_sends_notification` - Complete notify workflow when user switched windows - End-to-end validation of notification sending
- `test_notify_workflow_user_stayed_no_notification` - Complete notify workflow when user stayed on same window - End-to-end validation of intelligent notification suppression
- `test_cleanup_workflow_removes_session` - Complete cleanup workflow with age-based file removal - End-to-end validation of session cleanup functionality
- `test_wrapper_performance` - Bash wrapper returns immediately without waiting for Python - Critical for non-blocking hook execution in Claude Code
- `test_notify_sent_when_same_window_but_tmux_detached` - Notify sends notification when same window but user switched tmux sessions - Detects intra-window tmux session switches
- `test_notify_sent_when_same_iterm2_window_but_different_tab` - Notify sends local notification when iTerm2 tab changed in same window - Enables tab-level away detection in iTerm2
- `test_dedup_preserves_iterm2_session_id` - check_deduplication preserves iTerm2 session ID on timestamp rewrite - Prevents silent loss of tab restore on second-and-later notifications
- `test_file_locking_prevents_race_conditions` - File locking prevents race conditions and preserves tmux session ID - Essential for preventing duplicate notifications
- `test_push_uses_extended_intervals_when_tmux_attached_desktop` - Desktop mode uses extended idle check intervals when tmux attached - Ensures attached tmux sessions use attached idle check intervals

### TestDataParsing (4 tests) - Hook Data Contract Testing
- `test_hookdata_from_stdin_valid_json` - JSON input parsing from Claude Code hooks - Core functionality for receiving hook data
- `test_hookdata_from_stdin_invalid_json_raises_error` - Malformed JSON input error handling - Prevents silent failures when Claude Code sends bad data
- `test_hookdata_filters_unexpected_fields` - Filtering unknown fields from hook data - Maintains compatibility when Claude Code adds new fields
- `test_hookdata_defaults_applied` - Default values for missing optional fields - Ensures predictable behavior with minimal hook data

### TestSessionFileOperations (3 tests) - Session Persistence Testing
- `test_save_window_id_creates_file` - Session file creation with window ID, timestamp, and tmux session ID - Essential for window focus restoration functionality
- `test_load_window_id_reads_saved_id` - Session file reading and window ID extraction - Required for determining original window to focus
- `test_load_window_id_missing_file_raises_error` - Error handling when session file doesn't exist - Prevents undefined behavior when files are missing

### TestRemoteMode (6 tests) - Remote SSH Session Testing
- `test_remote_session_detection` - SSH environment variable detection for remote mode - Essential for determining desktop vs remote mode behavior
- `test_remote_mode_init_uses_placeholder` - Remote mode uses placeholder window ID with tmux session ID - Ensures remote mode captures tmux context
- `test_remote_mode_skips_local_notification` - Remote mode skips terminal-notifier - Validates remote mode behavior without local notifications
- `test_push_uses_extended_intervals_when_tmux_attached` - Push uses extended idle check intervals when tmux attached - Ensures attached sessions get delayed push instead of suppression
- `test_tty_idle_detection` - TTY access time calculation for remote idle detection - Critical for remote push notification timing
- `test_baseline_idle_detection` - User activity detection during check periods - Ensures push notifications only sent when user truly idle

### TestTmuxSessionDetection (6 tests) - Tmux Session ID and Attachment Testing
- `test_get_tmux_session_id_success` - Captures tmux session ID when running in tmux - Core tmux detection functionality
- `test_get_tmux_session_id_not_in_tmux` - Returns None when tmux is not installed - Graceful degradation
- `test_get_tmux_session_id_timeout` - Returns None on tmux command timeout - Prevents hanging
- `test_is_tmux_session_attached_true` - Detects attached tmux session with active clients - Core attachment checking
- `test_is_tmux_session_attached_false` - Detects detached tmux session with no clients - Ensures notifications sent when detached
- `test_is_tmux_session_attached_tmux_unavailable` - Returns False when tmux not installed - Graceful degradation

### TestTitleFormat (14 tests) - Customizable Notification Title Testing
- `test_default_title_when_env_not_set` - Default "Claude Code" title when CC_NOTIFIER_TITLE_FORMAT not set
- `test_custom_format_with_dir_token` - {dir} token resolves to directory basename
- `test_custom_format_with_hostname_token` - {hostname} token resolves to socket.gethostname()
- `test_custom_format_with_tmux_session_token` - {tmux_session} token resolves via tmux command
- `test_tmux_session_empty_when_not_in_tmux` - {tmux_session} resolves to empty string when tmux unavailable
- `test_custom_format_with_cwd_token` - {cwd} token resolves to full working directory
- `test_custom_format_with_all_tokens` - Format string with all built-in tokens combined
- `test_env_var_token` - {env:VAR_NAME} resolves to environment variable value
- `test_env_var_token_missing_var` - {env:VAR_NAME} resolves to empty string when var not set
- `test_env_var_token_mixed_with_builtins` - {env:VAR} mixed with built-in tokens
- `test_resolve_title_tokens_returns_all_keys` - Token dict contains all expected keys
- `test_resolve_title_tokens_skips_tmux_when_not_in_template` - Skips tmux subprocess call when {tmux_session} not in template - Prevents unnecessary subprocess calls
- `test_create_notification_data_uses_format_title` - Notification data uses format_title for both local and push
- `test_create_notification_data_default_preserves_originals` - Default title preserves original behavior for both local and push modes
### TestPushNotificationURL (5 tests) - Push Notification URL Construction & Encoding
- `test_build_push_url_substitutes_placeholders` - Placeholder substitution for {cwd} and {session_id} - Core URL template functionality
- `test_build_push_url_preserves_query_parameters` - Query parameters (?, &, =) preserved in custom URLs - Ensures URL schemes like blinkshell:// work correctly
- `test_build_push_url_returns_none_when_not_configured` - Returns None when CC_NOTIFIER_PUSH_URL not set - Backward compatibility validation
- `test_build_push_url_with_special_characters_in_path` - Special characters (spaces, hyphens) in file paths - Documents user responsibility for encoding
- `test_push_url_survives_urlencode` - URL survives urllib.parse.urlencode() for POST body - Critical validation that URLs work through Pushover API encoding

---

## test_integrations.py (9 tests) - External System Boundaries & Integration Testing

### TestHammerspoonIntegration (1 test) - Consolidated External System Testing
- `test_hammerspoon_cli_integration` - Hammerspoon CLI success, timeout, and error scenarios - Comprehensive testing of window management integration in a single consolidated test

### TestExternalSystemErrorHandling (2 tests) - System Boundary Error Testing
- `test_json_parsing_error_recovery` - Error handling for malformed JSON from Claude Code hooks - Prevents undefined behavior with bad hook data
- `test_corrupted_session_file_handling` - Error handling for corrupted/unreadable session files - Prevents undefined behavior with bad file data

### TestNotificationSystemIntegration (4 tests) - Notification Boundary Testing
- `test_create_focus_command_generates_correct_script` - Focus command generation for window restoration - Essential for click-to-focus functionality
- `test_create_focus_command_includes_iterm2_tab_restore` - Focus command adds iTerm2 tab/session restore step when session ID exists - Ensures click-to-focus can restore exact iTerm2 tab
- `test_terminal_notifier_command_construction` - Command construction for notification scenarios and focus parameters - Validates command-line argument generation and click-to-focus integration
- `test_basic_error_logging_functionality` - Basic error logging to file with error details - Essential for troubleshooting issues in production

### TestITerm2Integration (2 tests) - iTerm2-Specific Integration Testing
- `test_is_iterm2_app_detection` - Detects iTerm2 app paths reliably - Gates iTerm2-only tab logic without affecting other apps
- `test_get_iterm2_focused_session_id` - Captures focused iTerm2 session ID with graceful fallback - Ensures robust tab identity capture for notifications