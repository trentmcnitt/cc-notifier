# Changelog

All notable changes to cc-notifier are documented here. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- `CC_NOTIFIER_DISABLE=1` turns every cc-notifier hook into a no-op, so headless or scheduled Claude runs can skip notifications without changing hook config. Now that v0.4.0 no longer crashes under a minimal `PATH`, such runs would otherwise send push notifications.

### Fixed

- `cc-notifier --version` and `--help` through the installed wrapper now print their output. They used to print nothing, because output went to `/dev/null`, and waited on stdin when nothing was piped in.
- The pip entry point works: `pip install .` then `cc-notifier --version` prints the version instead of the "should not be run directly" error. Hook commands are still guarded.

## [0.4.0] - 2026-09-27

### Added

- **iTerm2 tab awareness.** Switching to another tab in the same iTerm2 window now counts as switching away, and clicking the notification restores the original tab. ([#9](https://github.com/trentmcnitt/cc-notifier/pull/9), [@dgokcin](https://github.com/dgokcin))
- **tmux session tracking.** Switching to another tmux session inside the same terminal window triggers a notification. Without Hammerspoon, an attached tmux session suppresses the local notification, and push notifications use separate idle-check intervals while the session is attached. ([#5](https://github.com/trentmcnitt/cc-notifier/pull/5), [@lamdor](https://github.com/lamdor))
- **Custom notification titles** via `CC_NOTIFIER_TITLE_FORMAT`, with `{dir}`, `{cwd}`, `{hostname}`, `{tmux_session}`, and `{env:VAR}` placeholders. `CC_NOTIFIER_PUSH_URL` accepts the same placeholders. ([#2](https://github.com/trentmcnitt/cc-notifier/pull/2), [@lamdor](https://github.com/lamdor))
- **`--icon <path>`** shows a custom image in local notifications. ([#13](https://github.com/trentmcnitt/cc-notifier/pull/13), [@wozniakos10](https://github.com/wozniakos10))
- The session file stores the originating app, so error notifications focus the right app, and Hammerspoon shows an error notification when it can't focus a window.
- MIT `LICENSE` file.
- GitHub Actions CI: ruff, mypy, vulture, and shellcheck, plus the test suite on Python 3.9 through 3.14 on macOS.

### Changed

- The recommended `SessionStart` matcher is now `startup|resume|clear|fork`, as defense in depth for the compaction fix below.
- The README drops the `Stop` hook matcher, which Claude Code ignores, and narrows the `Notification` matcher to `permission_prompt|elicitation_dialog`.
- `terminal-notifier` is found via `PATH` and both Homebrew prefixes, so local notifications work on Intel Macs.
- The README documents requirements (including Hammerspoon's Accessibility permission), all options and placeholders, and links the cross-Space focusing research log.

### Fixed

- Compaction no longer overwrites the captured window. `SessionStart` also fires on compaction, and `init` used to record whatever window was focused at that moment, so click-to-focus and switched-away detection could target the wrong window. `init` now keeps the existing session file when `source` is `compact`. No settings change needed.
- `notify` no longer fails when the session file is missing, for example when cc-notifier was installed mid-session. ([#11](https://github.com/trentmcnitt/cc-notifier/issues/11))
- A missing Hammerspoon no longer crashes `init`; notifications still arrive, without click-to-focus. ([#3](https://github.com/trentmcnitt/cc-notifier/pull/3), [@lamdor](https://github.com/lamdor))
- A failed local notification no longer prevents the push notification.
- `install.sh` checks that the Hammerspoon CLI actually responds, and its README links point at sections that exist.
- Quick Start includes the `hs.ipc.cliInstall()` step and a reload command that doesn't hang.
- The desktop push idle check no longer crashes `notify` when the hook's `PATH` lacks `/usr/sbin`. `ioreg` is now resolved by absolute path, so push notifications from such sessions (e.g. scheduled or headless runs) are delivered again.
- Tests no longer write to the developer's real `~/.cc-notifier` log.

## [0.3.0] - 2025-10-23

See the [v0.3.0 release](https://github.com/trentmcnitt/cc-notifier/releases/tag/v0.3.0).

[Unreleased]: https://github.com/trentmcnitt/cc-notifier/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/trentmcnitt/cc-notifier/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/trentmcnitt/cc-notifier/releases/tag/v0.3.0
