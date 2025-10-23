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

## Development Commands

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
- `make check-ci` - Run quality checks with fail-fast for CI
- `make clean` - Clean up temporary files and caches

### Development Setup

**Virtual Environment Required:** Modern Python tooling requires a virtual environment:

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

**Development Workflow:**
```bash
# Format and lint code
make format && make lint

# Run type checking
make typecheck

# Run tests
make test

# Complete quality check (runs all tools)
make check
```

## Architecture

The system is implemented in Python with a modern package structure and comprehensive type annotations:

### Package Structure
```
cc-notifier/
├── cc_notifier.py               # Consolidated monolithic script
├── cc-notifier                  # Executable script entry point
├── manual_testing.py            # Interactive testing utility
├── install.sh                   # Installation script with dependency setup
├── uninstall.sh                 # Clean uninstallation script
├── tests/
│   ├── test_core.py             # Core functionality and workflow tests
│   ├── test_integrations.py     # External system integration tests
│   └── tests.context.md         # Testing context documentation
├── pyproject.toml               # Modern Python project configuration
├── Makefile                     # Development workflow commands
├── .pre-commit-config.yaml      # Quality enforcement hooks
├── README.md                    # Project documentation
├── CLAUDE.md                    # Claude Code development guidance
├── streamlining_plan.md         # Development planning document
└── .gitignore                   # Git ignore patterns
```

### Command Architecture
- **cc-notifier init** - SessionStart hook: Captures focused window ID (desktop) or saves placeholder (remote)
- **cc-notifier notify** - Stop/Notification hooks: Sends local notifications (desktop) or push notifications (remote)
- **cc-notifier cleanup** - SessionEnd hook: Cleans up session files (both modes)

### Consolidated Architecture
- **cc_notifier.py** - Single monolithic file containing all functionality organized in clear sections:
  - Core utilities and session management (HookData dataclass, file operations)
  - Hammerspoon CLI integration for cross-space window management
  - Notification generation and terminal-notifier integration
  - CLI command dispatch and main entry point


### Key Components

- **Command dispatcher**: `cc-notifier` main command with subcommands (init, notify, cleanup)
- **Installation**: Single directory location (`~/.cc-notifier/`)
- **Session tracking**: Window IDs stored in `/tmp/cc_notifier/{session_id}`
- **Window management**: Uses Hammerspoon CLI for cross-space window focusing via `hs.window.filter`
- **Notifications**: terminal-notifier with `-execute` parameter for click-to-focus functionality
- **Intelligence**: Only notifies if user actually switched away from original window
- **Self-contained**: All files in single directory, no PATH dependencies

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

Development dependencies are defined in `pyproject.toml` and can be installed with `make install` in a virtual environment.

## Testing Framework

The project uses an optimized, behavior-focused testing approach:

- **pytest** - Modern Python testing framework
- **Behavior-focused tests** - Tests validate user-visible behaviors rather than implementation details
- **2-file organization** - `test_core.py` (core functionality tests) for essential behaviors, `test_integrations.py` (system integration tests) for external boundaries
- **Right-sized testing** - Targeted behavior-focused tests with target 1.5:1 to 2:1 test-to-code ratio focusing on essential functionality
- **Manual Testing** - Interactive testing utility (`manual_testing.py`) for validating notification functionality
- **Type checking** - All modules have comprehensive type annotations validated by mypy
- **Quality gates** - Pre-commit hooks enforce code quality standards

**Testing Philosophy**: Quality without bloat - test complexity matches project complexity. Every test must catch a bug that affects user experience. Tests focus on essential user-facing functionality and system integration contracts rather than internal implementation details.

**Testing Target**: Target 1.5:1 to 2:1 ratio for testing code to functional code. This provides comprehensive validation while enabling rapid development and refactoring without coverage bureaucracy.

**Critical: Tests must fail when production logic changes.** All tests validate real functionality and catch actual bugs. Tests enable refactoring rather than hindering it by focusing on behaviors, not implementation details.

### Running Tests
Prepend all commands with `source .venv/bin/activate` in order to use the virtual environment.
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

The project enforces strict quality standards suitable for AI-generated code:

- **Type Safety** - Full mypy type checking with strict configuration
- **Modern Linting** - Ruff with AI-focused rules for clean, maintainable code
- **Security Scanning** - Bandit for vulnerability detection
- **Dead Code Detection** - Vulture to catch unused code
- **Consistent Formatting** - Ruff formatter for consistent code style
- **Pre-commit Hooks** - Automatic quality enforcement on every commit

All configuration is centralized in `pyproject.toml` following modern Python standards.
- Even though this is a simple project, it maintains professional quality standards and implements configurations aimed to help with AI-assisted development.

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

### Debugging Workflow

1. **Clear console**: `hs -c "hs.console.clearConsole()"`
2. **Test operation**: Run cc-notifier or test command
3. **Check console**: View logs with timestamps to correlate errors
4. **Reload if needed**: `hs -c "hs.reload()"` if Hammerspoon gets stuck


Check out [Hammerspoon docs](https://www.hammerspoon.org/docs/) for more commands and troubleshooting tips, like [hs.logger](https://www.hammerspoon.org/docs/hs.logger.html)

## Code Philosophy

**Balance simplicity with quality - this is a simple notification tool with professional standards.**

**CRITICAL: Write super lean, minimal code. This is not an enterprise application.**

### Core Principles
- **Lean and Minimal First** - Write the absolute minimum code necessary. Every line must justify its existence.
- **Simplicity Over Everything** - Keep functions small and focused, ask "Could this be simpler?" before adding complexity
- **No Enterprise Bloat** - This is a small, simple project. Resist the urge to over-architect or add unnecessary abstractions.
- **Quality Without Bloat** - Use modern tooling and strict standards without over-engineering
- **Type Safety** - Leverage Python's type system for better maintainability and IDE support
- **Testable Design** - Write code that can be easily tested and validated
- **Professional Standards** - Follow Python best practices even for simple tools

### Development Guidelines
- **Git Operations** - Never commit or push changes without explicit user consent. Always ask before running `git commit` or `git push` commands.


## Installation

Run `./install.sh` to set up dependencies and generate Claude Code hook configuration. The installer provides JSON configuration to add to `~/.claude/settings.json`.

# Context Files (denoted by the .context.md file extension)

Context Files (*.context.md) provide AI assistants with helpful, and contain information that aids understanding of the repository.

**Location**: Scattered throughout the repository, and should be located in the same directory as the code/documentation they describe.

Known Context Files (and their associated files):
- `./cc_notifier.context.md`: `cc_notifier.py`
- `./tests/tests.context.md`: All tests in the `tests/` directory

**Usage**: 
- Treat these files as the source of truth over code structure (or architectural) inference
- Content varies and can cover process flows, cataloging of functions/classes, detailed explanations of complex logic, and any other information that aids understanding
- IF A FILE HAS AN ASSOCIATED CONTEXT FILE, YOU MUST READ THAT FILE BEFORE WORKING WITH THE ASSOCIATED FILE
- Whenever working with a file that has an associated `.context.md`, read that file first to understand the context

**Style**: Freeform, meant to be as concise as possible, while still being optimally helpful. Typically uses things like bullet points and other formatting to keep things scannable, concise, and easy to digest. Uses markdown formatting.