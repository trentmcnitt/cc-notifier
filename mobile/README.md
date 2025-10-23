# Mobile Development Workflow

Continue Claude Code sessions on your phone via push notifications and Blink Shell.

## What's Possible

- Start a coding task on your desktop
- Walk away
- Get a push notification on your phone when the task completes
- **Tap the notification** → Blink Shell auto-opens → you're back in the exact conversation
- Continue coding from your phone
- Switch back to desktop whenever you want

Powered by cc-notifier + mosh + tmux + Blink Shell.

## How It Works

When Claude Code finishes a task and you're away from your computer:

1. cc-notifier detects you're idle and sends a push notification
2. Notification contains custom URL (configured via `CC_NOTIFIER_PUSH_URL`)
3. You tap the notification → Pushover app opens showing the URL
4. Tap the URL → Blink Shell opens via URL scheme
5. Blink executes `mosh-cc-resume.sh` with session details (`{session_id}`, `{cwd}`)
6. Script reconnects via mosh and resumes exact Claude Code session in tmux
7. You're coding on your phone

## Prerequisites

### Required
- **Remote server** with SSH access (your desktop Mac or a dedicated server)
- **[mosh](https://github.com/mobile-shell/mosh)** server installed on remote machine
- **[tmux](https://github.com/tmux/tmux)** installed on remote machine
- **[Blink Shell](https://github.com/blinksh/blink)** iOS app (supports mosh and URL schemes)
- **[Pushover](https://pushover.net)** account for push notifications
- **cc-notifier** installed and configured on remote machine

### Recommended
- **[Tailscale](https://github.com/tailscale/tailscale)** or similar for secure remote access

## Installation

### 1. Install Scripts on Remote Server

Copy the scripts to a location in your PATH (e.g., `~/bin/`):

```bash
# On your remote server
mkdir -p ~/bin
cp mosh-cc-resume.sh ~/bin/
cp tmux-idle-cleanup.sh ~/bin/
chmod +x ~/bin/mosh-cc-resume.sh ~/bin/tmux-idle-cleanup.sh
```

### 2. Configure Blink Shell

**Add Host Configuration:**
- **Host**: Your server hostname (e.g., `mbp`)
- **Connection**: Use mosh (not SSH)
- **User**: Your username
- **Key**: Your SSH key

**Set Up URL Key:**
1. Open Blink Shell → Settings → Keys
2. Create a new key for URL scheme access
3. Note the key identifier

### 3. Configure cc-notifier Push URL

In Claude Code settings (`~/.claude/settings.json`) on your remote server:

```json
{
  "env": {
    "PUSHOVER_API_TOKEN": "your_pushover_app_token",
    "PUSHOVER_USER_KEY": "your_pushover_user_key",
    "CC_NOTIFIER_PUSH_URL": "blinkshell://run?key=YOUR_BLINK_KEY&cmd=mosh mbp -- ~/bin/mosh-cc-resume.sh {session_id} {cwd}"
  }
}
```

Customize `mbp` to match your Blink Shell host name.

Placeholders `{session_id}` and `{cwd}` are replaced by cc-notifier.

### 4. (Optional) Auto-start Cleanup Daemon

Add to `~/.zshrc` or `~/.bashrc` on the remote server:

```bash
if [[ -n "$SSH_CONNECTION" ]]; then
    pgrep -f "tmux-idle-cleanup.sh" > /dev/null || nohup ~/bin/tmux-idle-cleanup.sh > /dev/null 2>&1 &
fi
```
