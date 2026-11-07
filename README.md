# claude-reels

Instagram Reels in a phone-sized, always-on-top Chrome window, but only while Claude Code is thinking. Plus a tiny tracker for how long you've waited.

Author: Ahmadh Hassan. Windows + PowerShell + Chrome only.

- `reels.ps1`: opens `instagram.com/reels` as a 390x844 app window (iPhone user agent, touch events) at the top-right of the screen, pinned above other windows. Uses its own Chrome profile, so log in once.
- `reeltime.py`: `start` / `stop` log how long each prompt took; `report` prints totals; `selftest` runs a check.

## Install

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

Restart Claude Code. Stats: `python -I reeltime.py report`.

The `Stop` hook only kills Chrome processes launched with the `claude-reels-profile` folder, never your normal Chrome. Window size is `$W`/`$H` at the top of `reels.ps1`.
