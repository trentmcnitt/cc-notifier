# Contributing

Thanks for helping improve cc-notifier. Bug reports, fixes, and small features are all welcome.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
make install
pre-commit install
```

## Before opening a PR

- Run `make check`: formatting, lint, type checking, tests, dead-code detection, and shellcheck. CI runs the same checks, plus the tests on Python 3.9 through 3.14.
- Add or update tests for behavior changes. Tests should check what the user sees (was a notification sent, which window gets focus), not implementation details.
- Update the matching `*.context.md` file when you change `cc_notifier.py` or the tests. `tests/tests.context.md` lists every test.
- Keep it small. cc-notifier is one standard-library Python file on purpose, so avoid new runtime dependencies.

## Reporting a bug

Please include your macOS version, terminal or IDE, and whether you use tmux or iTerm2. A debug log helps most: add `--debug` to your hook commands, reproduce the problem, and attach the relevant lines from `~/.cc-notifier/cc-notifier.log`.
