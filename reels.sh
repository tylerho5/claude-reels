#!/bin/bash
# Instagram Reels in a phone-sized Chrome window pinned above other windows (macOS).
# Usage: reels.sh [open|close]     Windows users: see reels.ps1.
set -u

PROFILE="${CLAUDE_REELS_PROFILE:-$HOME/Library/Application Support/claude-reels-profile}"
CHROME="${CLAUDE_REELS_CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
URL="${CLAUDE_REELS_URL:-https://www.instagram.com/reels/}"
W="${CLAUDE_REELS_WIDTH:-390}"   # iPhone 14 viewport; edit to taste
H="${CLAUDE_REELS_HEIGHT:-844}"
PAD=20                           # gap from the right edge of the screen
TOP=36                           # clears the menu bar
UA="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"

HERE=$(cd -- "$(dirname -- "$0")" && pwd)
PY=$(command -v python3 || echo /usr/bin/python3)
TMP="${TMPDIR:-/tmp}"
LOG="${TMP%/}/claude-reels.log"

open_window() {
  if [ ! -x "$CHROME" ]; then
    echo "claude-reels: Chrome not found at $CHROME" >&2
    return 1
  fi

  # Already open: just pin it above other windows again.
  if out=$("$PY" "$HERE/macwin.py" float --marker "$PROFILE" 2>&1); then
    printf '%s\n' "$out"
    return 0
  fi

  read -r _dx _dy dw _dh <<<"$("$PY" "$HERE/macwin.py" display)"
  dw=${dw:-1512}
  x=$(( dw - W - PAD ))
  [ "$x" -lt 0 ] && x=0

  nohup "$CHROME" \
    --user-data-dir="$PROFILE" \
    --app="$URL" \
    --window-size="$W,$H" \
    --window-position="$x,$TOP" \
    --user-agent="$UA" \
    --touch-events=enabled \
    --autoplay-policy=no-user-gesture-required \
    --no-first-run --no-default-browser-check \
    >/dev/null 2>&1 &
  disown 2>/dev/null

  # Pin the window once it exists. Out of process so a hook returns immediately.
  nohup "$PY" "$HERE/macwin.py" float --marker "$PROFILE" --wait 20 >>"$LOG" 2>&1 &
  disown 2>/dev/null
  echo "opening $URL (log: $LOG)"
}

# Only processes started with our own profile folder, never your normal Chrome.
close_window() {
  if pkill -f -- "--user-data-dir=$PROFILE"; then
    echo "closed"
  fi
  return 0
}

case "${1:-open}" in
  open) open_window ;;
  close) close_window ;;
  *)
    echo "usage: $0 [open|close]" >&2
    exit 2
    ;;
esac
