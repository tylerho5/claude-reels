# claude-reels

Instagram Reels in a phone-sized, always-on-top Chrome window, but only while Claude Code is thinking. Plus a tiny tracker for how long you've waited.

Author: Ahmadh Hassan. Chrome only: PowerShell on Windows, bash on macOS.

- `reels.ps1` / `reels.sh`: opens `instagram.com/reels` as a 390x844 app window (iPhone user agent, touch events) at the top-right of the screen, pinned above other windows. Uses its own Chrome profile, so log in once.
- `macwin.py` (macOS only): the window-server calls `reels.sh` relies on. `display` prints the main display bounds, `float` pins a window above other windows.
- `reeltime.py`: `start` / `stop` log how long each prompt took; `report` prints totals; `selftest` runs a check.

## Install on macOS

Copy the three files somewhere (e.g. `~/.claude/hooks/`), make the scripts executable, and add this to `~/.claude/settings.json`, fixing the paths:

```bash
chmod +x ~/.claude/hooks/reels.sh ~/.claude/hooks/macwin.py
```

```json
"hooks": {
  "UserPromptSubmit": [{ "hooks": [{
    "type": "command", "shell": "bash",
    "command": "python3 -I \"$HOME/.claude/hooks/reeltime.py\" start; \"$HOME/.claude/hooks/reels.sh\" open"
  }]}],
  "Stop": [{ "hooks": [{
    "type": "command", "shell": "bash",
    "command": "python3 -I \"$HOME/.claude/hooks/reeltime.py\" stop; \"$HOME/.claude/hooks/reels.sh\" close"
  }]}]
}
```

Always-on-top is best effort on macOS. `macwin.py float` raises the window's level through the window server — the same private call yabai uses — and `reels.sh` keeps that request asserted from a small background process for as long as the window is open. Recent macOS releases accept the change and then ignore it, so the window can still end up behind other apps. It does open every prompt, right-aligned at 390x844, and takes focus. For the level to have any chance of applying, the app that runs Claude Code (Terminal, iTerm2, the Claude Code app) needs Accessibility permission under System Settings → Privacy & Security → Accessibility. Launch output goes to `$TMPDIR/claude-reels.log`.

## Install on Windows

Copy both files somewhere (e.g. `~/.claude/hooks/`) and add this to `~/.claude/settings.json`, fixing the paths:

```json
"hooks": {
  "UserPromptSubmit": [{ "hooks": [{
    "type": "command", "shell": "powershell",
    "command": "python -I 'C:\\path\\to\\reeltime.py' start; Start-Process powershell -WindowStyle Hidden -ArgumentList '-NoProfile','-File','C:\\path\\to\\reels.ps1'"
  }]}],
  "Stop": [{ "hooks": [{
    "type": "command", "shell": "powershell",
    "command": "python -I 'C:\\path\\to\\reeltime.py' stop; Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | Where-Object { $_.CommandLine -like '*claude-reels-profile*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
  }]}]
}
```

## Both

Restart Claude Code. Stats: `python3 -I reeltime.py report` (`python -I` on Windows).

Window size is `$W`/`$H` at the top of `reels.sh` or `reels.ps1`. The `Stop` hook only kills Chrome processes launched with the `claude-reels-profile` folder, never your normal Chrome. Log in once in the reels window; the session lives in `~/Library/Application Support/claude-reels-profile` on macOS and `%LOCALAPPDATA%\claude-reels-profile` on Windows.
