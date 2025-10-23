# Mobile Development Workflow

Code from anywhere - desktop, phone, bed, on a walk. This workflow lets you seamlessly continue your Claude Code sessions across devices.

## What's Possible

- Start a coding task on your desktop
- Walk away (go to bed, take a walk, commute)
- Get a push notification on your phone when the task completes
- **Tap the notification** → Blink Shell auto-opens → you're back in the exact conversation
- Continue coding from your phone
- Switch back to desktop whenever you want

All powered by cc-notifier + mosh + tmux + Blink Shell.

## The Magic: How It Works

When Claude Code finishes a task and you're away from your computer:

1. **cc-notifier detects you're idle** and sends a push notification to your phone
2. **Notification contains a custom URL** configured via `CC_NOTIFIER_PUSH_URL`
3. **You tap the notification** → Pushover app opens showing the URL link
4. **Tap the URL link** → Blink Shell opens via URL scheme
5. **Blink executes `mosh-cc-resume.sh`** with your session details (`{session_id}` and `{cwd}`)
6. **Script reconnects via mosh** and resumes your exact Claude Code session in tmux
7. **You're coding on your phone** in seconds, continuing right where you left off

Whether you're on a walk, in bed, or on the train - your development environment follows you.

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
  - Provides encrypted WireGuard VPN
  - Works seamlessly with mosh
  - Allows connection from anywhere

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

#### Add Host Configuration
In Blink Shell, add your remote server host:
- **Host**: Your server hostname (e.g., `mbp` or `my-server`)
- **Connection**: Use mosh (not SSH)
- **User**: Your username
- **Key**: Your SSH key

#### Set Up URL Key (Critical!)
1. Open Blink Shell → Settings → Keys
2. Create a new key for URL scheme access
3. Note the key identifier (you'll need it for the URL)

This key allows the URL scheme to execute commands in Blink Shell.

### 3. Configure cc-notifier Push URL

On your remote server, set the `CC_NOTIFIER_PUSH_URL` environment variable in Claude Code settings (`~/.claude/settings.json`):

```json
{
  "env": {
    "PUSHOVER_API_TOKEN": "your_pushover_app_token",
    "PUSHOVER_USER_KEY": "your_pushover_user_key",
    "CC_NOTIFIER_PUSH_URL": "blinkshell://run?key=YOUR_BLINK_KEY&cmd=mosh mbp -- ~/bin/mosh-cc-resume.sh {session_id} {cwd}"
  }
}
```

**Breaking down the URL:**
- `blinkshell://run` - Blink Shell URL scheme
- `?key=YOUR_BLINK_KEY` - Your Blink Shell URL key (from step 2)
- `&cmd=mosh mbp` - Connect to your server via mosh
- `-- ~/bin/mosh-cc-resume.sh {session_id} {cwd}` - Execute resume script with session details
- `{session_id}` - Replaced by cc-notifier with actual Claude Code session ID
- `{cwd}` - Replaced by cc-notifier with current working directory

**Customize `mbp`** to match your Blink Shell host name.

### 4. (Optional) Auto-start Cleanup Daemon

Add to your `~/.zshrc` or `~/.bashrc` on the remote server:

```bash
# Auto-start tmux cleanup daemon on SSH connection
if [[ -n "$SSH_CONNECTION" ]]; then
    pgrep -f "tmux-idle-cleanup.sh" > /dev/null || nohup ~/bin/tmux-idle-cleanup.sh > /dev/null 2>&1 &
fi
```

This ensures orphaned tmux sessions get cleaned up automatically.

## Customization

### mosh-cc-resume.sh

Edit the script to match your preferences:

```bash
SESSION_NAME="claude_code_resume"  # Your preferred tmux session name
NOTIFY_WINDOW=9                    # Window number for notifications (prevents accumulation)
```

**Paths to adjust:**
- `~/bin/tmux-idle-cleanup.sh` - If your cleanup script is elsewhere
- `~/Library/Keychains/login.keychain-db` - If using different keychain path

### tmux-idle-cleanup.sh

Tune the cleanup behavior:

```bash
IDLE_MINUTES=600  # Kill sessions after 10 hours (adjust as needed)
MAX_HOURS=24      # Daemon auto-shutdown after 24 hours
```

**Check interval:**
- Default: 1 hour (`sleep 3600`)
- For more aggressive cleanup, reduce the sleep time

## How the Scripts Work

### mosh-cc-resume.sh

**Purpose:** Automatically resume your Claude Code session when tapped from push notification.

**Key Features:**
- Uses tmux window 9 for notifications (prevents window accumulation)
- Handles keychain unlock if needed (Mac-specific)
- Uses `--dangerously-skip-permissions` to bypass permission prompts

**Why `--dangerously-skip-permissions`?**

Claude Code has known issues with API key persistence over mosh/SSH (see [GitHub issue #5515](https://github.com/anthropics/claude-code/issues/5515)). The flag is safe here because:
- You've already granted permissions in the original session
- You're the same authenticated user
- The session is being resumed, not started fresh

**Related Issues:**
- [#5515](https://github.com/anthropics/claude-code/issues/5515) - API key persistence
- [#642](https://github.com/anthropics/claude-code/issues/642) - mosh support
- [#5957](https://github.com/anthropics/claude-code/issues/5957) - SSH support

### tmux-idle-cleanup.sh

**Purpose:** Prevent orphaned tmux sessions from accumulating on your server.

**How It Works:**
1. Runs as background daemon
2. Checks all tmux sessions every hour
3. Kills detached sessions idle for longer than `IDLE_MINUTES`
4. Never kills sessions while you're attached
5. Auto-shutdowns when no sessions remain or after `MAX_HOURS`

**Logs:** Check `/tmp/tmux-cleanup.log` to see cleanup activity.

## Troubleshooting

### Push notification doesn't contain URL
- Verify `CC_NOTIFIER_PUSH_URL` is set in `~/.claude/settings.json`
- Check that Pushover credentials are configured
- Ensure you're in remote mode (SSH_CONNECTION environment variable set)

### Blink Shell doesn't open when tapping URL
- Verify Blink Shell URL key is correct in the URL
- Check that host name matches your Blink Shell configuration
- Ensure Blink Shell app is installed on your phone

### Session doesn't resume
- Check that `mosh-cc-resume.sh` is executable: `chmod +x ~/bin/mosh-cc-resume.sh`
- Verify paths in script match your setup
- Check for errors in mosh connection (Blink Shell will show these)

### Keychain unlock fails
- The script uses `security show-keychain-info` to detect if keychain is locked
- If automatic unlock fails, manually unlock before testing
- Adjust keychain path if yours differs from default

### Too many tmux sessions accumulating
- Ensure cleanup daemon is running: `pgrep -f tmux-idle-cleanup.sh`
- Reduce `IDLE_MINUTES` for more aggressive cleanup
- Check logs: `tail /tmp/tmux-cleanup.log`

## Testing the Workflow

### End-to-End Test
1. Start Claude Code on your desktop/server (via SSH)
2. Start a simple task: "just say hi"
3. Close your SSH connection or switch to another window
4. Wait for notification on your phone
5. Tap notification → tap URL link
6. Verify Blink Shell opens and resumes session

### Test Resume Script Directly
```bash
# SSH into your server and run:
~/bin/mosh-cc-resume.sh test_session_id /path/to/working/dir
```

This should create/attach to the tmux session.

## The Complete Stack

This workflow combines several battle-tested tools:

- **[cc-notifier](../)** - Intelligent notifications with push URL support
- **[Tailscale](https://github.com/tailscale/tailscale)** - Secure remote access
- **[mosh](https://github.com/mobile-shell/mosh)** - Resilient remote shell (handles network changes)
- **[tmux](https://github.com/tmux/tmux)** - Terminal multiplexer for session persistence
- **[Blink Shell](https://github.com/blinksh/blink)** - Professional iOS terminal with URL scheme support

Together, they enable a seamless desktop ↔ phone development workflow that just works.

## Tips & Best Practices

### Battery Life
- Close Blink Shell when done to save battery
- cc-notifier will still notify you when needed

### Network Changes
- mosh handles network transitions automatically
- Switch between WiFi and cellular without dropping connection

### Session Management
- Use descriptive tmux session names
- Let the cleanup daemon handle old sessions
- Check `tmux ls` occasionally to see active sessions

### Security
- Use Tailscale or similar VPN for secure remote access
- Keep SSH keys secure in Blink Shell
- The URL key in Blink Shell acts as authentication

## What Makes This Special

Unlike traditional remote development:
- **No manual reconnection** - Tap notification, instantly resume
- **Survives network changes** - mosh keeps connection alive
- **Context preservation** - Exact conversation, exact directory
- **True mobility** - Code from literally anywhere with internet

This is the future of remote development: your environment follows you, seamlessly.
