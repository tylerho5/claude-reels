# Opens Instagram Reels in a phone-sized, always-on-top Chrome window. No-op if already open.
$dir  = "$env:LOCALAPPDATA\claude-reels-profile"
$chrome = "C:\Program Files\Google\Chrome\Application\chrome.exe"
$W = 390; $H = 844   # iPhone 14 viewport; edit to taste
$ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"

Add-Type @"
using System; using System.Runtime.InteropServices;
public class W { [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr a, int x, int y, int cx, int cy, uint f); }
"@

function Find-Win {
  Get-CimInstance Win32_Process -Filter "Name='chrome.exe'" |
    Where-Object { $_.CommandLine -like "*$dir*" } |
    ForEach-Object { (Get-Process -Id $_.ProcessId -ErrorAction SilentlyContinue).MainWindowHandle } |
    Where-Object { $_ -ne 0 } | Select-Object -First 1
}

$h = Find-Win
if (-not $h) {
  Add-Type -AssemblyName System.Windows.Forms
  $x = [Windows.Forms.Screen]::PrimaryScreen.WorkingArea.Right - $W - 20
  Start-Process $chrome "--user-data-dir=`"$dir`" --app=https://www.instagram.com/reels/ --window-size=$W,$H --window-position=$x,20 --user-agent=`"$ua`" --touch-events=enabled --autoplay-policy=no-user-gesture-required"
  for ($i = 0; $i -lt 30 -and -not $h; $i++) { Start-Sleep -Milliseconds 300; $h = Find-Win }
}
# HWND_TOPMOST=-1; flags = NOSIZE|NOMOVE|SHOWWINDOW
if ($h) { [W]::SetWindowPos([IntPtr]$h, [IntPtr]-1, 0, 0, 0, 0, 0x43) | Out-Null }
