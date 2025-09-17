# Research Log: macOS Cross-Space Window Focusing

Technical discoveries that enabled a simple macOS notification system capable of returning focus to specific windows across Mission Control Spaces.

## Problem Statement

**Core Challenge**: Create a macOS notification system that can return focus to the exact window where Claude Code was originally running, not just the application.

**Requirements**:
- Click-to-focus functionality returning to specific window (not just app)
- Cross-Space functionality (macOS Mission Control Spaces)
- Cross-application support (VS Code, Cursor, IntelliJ, iTerm, etc.)
- Hook-triggered execution only (no background daemons)

**Why This Was Hard**: macOS Mission Control creates isolation boundaries that prevent conventional automation tools from accessing windows on different Spaces.

## Critical Technical Discoveries

### 1. AppleScript Cross-Space Limitations
**Discovery**: AppleScript and Accessibility APIs fundamentally cannot access windows on different Mission Control Spaces.
- **Impact**: Conventional automation approaches fail for cross-space scenarios
- **Evidence**: Multiple approaches tested, all hit the same OS-level boundary
- **Implication**: Need tool that can detect windows across spaces without requiring AppleScript

### 2. Shell-to-Window Linking Impossibility on macOS
**Discovery**: No reliable method exists to link a shell process to its parent window on macOS.
- **Impact**: Cannot determine which window launched Claude Code without external tracking
- **Attempted**: Process tree analysis, TTY correlation, parent process detection
- **Result**: All approaches failed on macOS due to sandboxing and process isolation
- **Implication**: Must rely on session-based tracking instead of process-based detection

### 3. Hammerspoon Cross-Space Detection Capability
**Discovery**: Hammerspoon can detect windows across Mission Control Spaces using window filters.
- **Key API**: `hs.window.filter` with space parameters can find windows across spaces
- **Why It Works**: Uses private APIs and system-level macOS integration
- **Implementation**: CLI access via `hs -c "command"` for shell integration
- **Limitation**: Detection works, but space switching capabilities were explored but not implemented

### 4. Dual-Filter Workaround
**Discovery**: Combining two window filters provides reliable cross-space window detection.
- **Method**: `setCurrentSpace(true)` + `setCurrentSpace(false)` combined
- **Why Not `setCurrentSpace(nil)`**: Can cause "infinite hangs and IPC port invalidation errors"
- **Evidence**: Documented in source code comments referencing GitHub issue #3276
- **Result**: Stable cross-space window detection without system hangs

## Current Implementation

The implemented solution uses a simple 3-step workflow:

1. **Session Initialization** - Capture focused window ID when Claude Code starts and store in session file
2. **Intelligent Notification** - Only notify if user switched away from original window, send notification with click-to-focus command
3. **Cross-Space Focus** - Use dual-filter approach to find window across all spaces and focus it directly

## Key Design Decisions

**Window ID Tracking** - Use session ID as persistent unique identifier for file naming. Claude Code always runs from focused window, so we capture that window's ID.

**Dual-Filter Approach** - Combining `setCurrentSpace(true)` + `setCurrentSpace(false)` provides stable cross-space detection without the system hangs that `setCurrentSpace(nil)` can cause.

## Known Failure Modes

1. **Silent Click Failures** - No fallback when target window not discoverable
2. **Space Detection Limits** - Hammerspoon may not find windows in long-inactive spaces
3. **No User Feedback** - Failed focus attempts provide no indication to user
4. **Dependency Sensitivity** - Requires Hammerspoon installation and proper configuration