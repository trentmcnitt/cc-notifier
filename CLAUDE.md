# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

cc-notifier is a notification system for Claude Code hooks supporting both local macOS and remote SSH environments. It provides intelligent notifications when Claude Code completes tasks, with click-to-focus functionality on macOS and push notifications for remote usage.

**Execution Model**: Runs asynchronously in the background, allowing Claude Code hooks to continue without waiting for notification completion.

**Environment Support** (v0.3.0+):
- **Desktop Mode**: macOS local usage with Hammerspoon window focusing and terminal-notifier
- **Remote Mode**: SSH usage with push notifications only (auto-detected via SSH environment variables)

**Hook Reference**: For authoritative details about hook behaviors, execution order, and available data, review the [official Claude Code hooks documentation](https://docs.claude.com/en/docs/claude-code/hooks).

See:
- @cc_notifier.context.md
- @tests/tests.context.md
- @README.md

## Context Files

Context files (`*.context.md`) provide AI assistants with essential architectural and behavioral context for associated code.

**Location**: Co-located with the code they describe.

Known context files:
- `./cc_notifier.context.md`: `cc_notifier.py`
- `./tests/tests.context.md`: All tests in the `tests/` directory

**Rules**:
- Read a file's associated context file before working with that file
- Update context files when modifying associated code
- Treat context files as the source of truth for architecture and code structure

**Style**: Concise, scannable, markdown-formatted. Bullet points preferred.

## Code Philosophy

Write the minimum code necessary. Every line must justify its existence. This is a small notification tool, not an enterprise application.

### Principles
- **Lean and Minimal** - Resist over-architecture. Ask "could this be simpler?" before adding complexity.
- **Quality Without Bloat** - Use modern tooling and strict standards without over-engineering.
- **Type Safety** - Leverage Python's type system for better maintainability and IDE support.
- **Testable Design** - Write code that can be easily tested and validated.
- **Git Operations** - Never commit or push without explicit user consent.

## Development Commands

All `make` commands require an active virtual environment: `source .venv/bin/activate`

### Setup
- `make install` - Install development dependencies (requires virtual environment)
- `make help` - Show all available commands

### Code Quality
- `make format` - Format code with ruff
- `make lint` - Comprehensive Python linting with ruff
- `make lint-fix` - Auto-fix linting issues
- `make typecheck` - Type checking with mypy
- `make shell-lint` - Lint shell scripts (shellcheck with severity=info, all checks enabled)

### Testing & Analysis
- `make test` - Run tests with pytest
- `make deadcode` - Find unused code with vulture

### Comprehensive Checks
- `make check` - Run all quality checks (format, lint, typecheck, test, deadcode, shell-lint)
- `make clean` - Clean up temporary files and caches

### Development Setup

**Virtual Environment Required:** Development dependencies must be installed in a virtual environment:

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install development dependencies
make install

# Set up pre-commit hooks for automatic quality enforcement
pre-commit install

# Run comprehensive quality checks
make check
```

## Architecture

Single-file Python implementation with type annotations:

### Package Structure
```
cc-notifier/
├── cc_notifier.py               # Main implementation (single file)
├── cc_notifier.context.md       # Architecture context for cc_notifier.py
├── cc-notifier                  # Bash wrapper (entry point)
├── manual_testing.py            # Interactive testing utility
├── install.sh                   # Installation script with dependency setup
├── uninstall.sh                 # Clean uninstallation script
├── tests/
│   ├── test_core.py             # Core functionality and workflow tests
│   ├── test_integrations.py     # External system integration tests
│   └── tests.context.md         # Testing context documentation
├── mobile/                      # Mobile development workflow scripts
│   ├── README.md
│   ├── mosh-cc-resume.sh
│   └── tmux-idle-cleanup.sh
├── pyproject.toml               # Modern Python project configuration
├── Makefile                     # Development workflow commands
├── .pre-commit-config.yaml      # Quality enforcement hooks
├── README.md                    # Project documentation
├── CLAUDE.md                    # Claude Code development guidance
└── .gitignore                   # Git ignore patterns
```

### Command Architecture
- **cc-notifier init** - SessionStart hook: Captures focused window ID (desktop) or saves placeholder (remote)
- **cc-notifier notify** - Stop/Notification hooks: Sends local notifications (desktop) or push notifications (remote)
- **cc-notifier cleanup** - SessionEnd hook: Cleans up session files (both modes)

### Key Components

- **cc_notifier.py** - Single-file implementation: core utilities, session management (HookData dataclass), Hammerspoon integration, notification system, CLI dispatch
- **cc-notifier** - Bash wrapper with subcommands (init, notify, cleanup)
- **Installation** - Single directory (`~/.cc-notifier/`), self-contained, no PATH dependencies
- **Session tracking** - Window ID, app path, and timestamp stored in `/tmp/cc_notifier/{session_id}`
- **Window management** - Hammerspoon CLI (`hs -c`) for cross-space window focusing via `hs.window.filter`
- **Notifications** - terminal-notifier with `-execute` parameter for click-to-focus functionality
- **Intelligence** - Only notifies if user actually switched away from original window

## Dependencies

### Runtime Dependencies
- **Python 3.9+** - Uses only standard library modules (no external packages required)

### Desktop Mode Dependencies
- **Hammerspoon** - Required for window focusing across macOS Spaces
- **terminal-notifier** - Required for macOS notifications with click actions

### Remote Mode Dependencies
- **Pushover account** (required) - Push notifications are the only notification method in remote mode

### Development Dependencies (optional, for development workflow)
- **ruff** - Modern Python linting and formatting
- **mypy** - Type checking for code quality
- **pytest** - Modern testing framework
- **vulture** - Dead code detection
- **pre-commit** - Git hook management

Development dependencies are defined in `pyproject.toml`. Install with `make install` in an active virtual environment.

## Testing Framework

The project uses an optimized, behavior-focused testing approach:

- **pytest** - Modern Python testing framework
- **Behavior-focused tests** - Tests validate user-visible behaviors rather than implementation details
- **2-file organization**:
  - `test_core.py` - Core functionality and essential behaviors
  - `test_integrations.py` - External system boundaries and integrations
- **Manual Testing** - Interactive testing utility (`manual_testing.py`) for validating notification functionality
- **Type checking** - All modules have comprehensive type annotations validated by mypy
- **Quality gates** - Pre-commit hooks enforce code quality standards

**Testing Philosophy**: Quality without bloat. Target 1.5:1 to 2:1 test-to-code ratio. Every test must catch a bug that affects user experience and must fail when production logic changes. Tests focus on behaviors, not implementation details.

### Running Tests
```bash
# Run all tests
make test

# Run tests with timing analysis (optional)
pytest -v --durations=5

# Run specific test file
pytest tests/test_core.py

# Manual testing (interactive)
python3 manual_testing.py system
```

## Code Quality Standards

The project enforces strict quality standards:

- **Type Safety** - Full mypy type checking with strict configuration
- **Modern Linting** - Ruff for linting and formatting
- **Security Scanning** - Bandit for vulnerability detection (pre-commit hook)
- **Dead Code Detection** - Vulture to catch unused code
- **Consistent Formatting** - Ruff formatter for consistent code style
- **Pre-commit Hooks** - Automatic quality enforcement on every commit

All configuration is centralized in `pyproject.toml` following modern Python standards.

## Hammerspoon Troubleshooting

### Essential Debugging Commands

```bash
# Reload Hammerspoon configuration
hs -c "hs.reload()"

# Clear Hammerspoon console for clean testing
hs -c "hs.console.clearConsole()"

# View recent console logs with timestamps
hs -c "
local console = hs.console.getConsole()
local lines = {}
for line in console:gmatch('[^\\n]+') do
    table.insert(lines, line)
end
for i = math.max(1, #lines-10), #lines do
    print(lines[i])
end"
```

### Debugging Workflow

1. **Clear console**: `hs -c "hs.console.clearConsole()"`
2. **Test operation**: Run cc-notifier or test command
3. **Check console**: View logs with timestamps to correlate errors
4. **Reload if needed**: `hs -c "hs.reload()"` if Hammerspoon gets stuck

Check out [Hammerspoon docs](https://www.hammerspoon.org/docs/) for more commands and troubleshooting tips, like [hs.logger](https://www.hammerspoon.org/docs/hs.logger.html)

## Installation

Run `./install.sh` to set up dependencies and generate Claude Code hook configuration. The installer provides JSON configuration to add to `~/.claude/settings.json`.
