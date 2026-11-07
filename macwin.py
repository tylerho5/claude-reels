#!/usr/bin/env python3
"""macOS window-server helpers for claude-reels. Used by reels.sh.

  macwin.py display              print the main display bounds as "x y w h"
  macwin.py float --marker TEXT  ask the window server to keep windows whose owner
                                 command line contains TEXT above other windows

Pinning sets the window level through the private SkyLight API CGSSetWindowLevel,
the same call yabai uses. Recent macOS releases accept the change and then ignore
it, so treat the pin as best effort: the window still opens at the right size and
place. `--hold` keeps the request asserted for as long as the window lives, which
is what a release where the level actually applies needs.
"""
import argparse
import ctypes
import os
import plistlib
import subprocess
import sys
import time

CORE_GRAPHICS = "/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics"
APP_SERVICES = "/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices"
SKYLIGHT = "/System/Library/PrivateFrameworks/SkyLight.framework/SkyLight"

# kCGFloatingWindowLevelKey: the level a normal floating window sits at.
FLOATING_LEVEL_KEY = 5


class CGPoint(ctypes.Structure):
    _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double)]


class CGSize(ctypes.Structure):
    _fields_ = [("width", ctypes.c_double), ("height", ctypes.c_double)]


class CGRect(ctypes.Structure):
    _fields_ = [("origin", CGPoint), ("size", CGSize)]


def _load():
    cg = ctypes.CDLL(CORE_GRAPHICS)
    cg.CGMainDisplayID.restype = ctypes.c_uint32
    cg.CGDisplayBounds.argtypes = [ctypes.c_uint32]
    cg.CGDisplayBounds.restype = CGRect
    cg.CGWindowLevelForKey.argtypes = [ctypes.c_int]
    cg.CGWindowLevelForKey.restype = ctypes.c_int
    cg.CGWindowListCopyWindowInfo.argtypes = [ctypes.c_uint32, ctypes.c_uint32]
    cg.CGWindowListCopyWindowInfo.restype = ctypes.c_void_p

    cf = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
    cf.CFPropertyListCreateData.argtypes = [
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_uint64, ctypes.c_void_p
    ]
    cf.CFPropertyListCreateData.restype = ctypes.c_void_p
    cf.CFDataGetLength.argtypes = [ctypes.c_void_p]
    cf.CFDataGetLength.restype = ctypes.c_long
    cf.CFDataGetBytePtr.argtypes = [ctypes.c_void_p]
    cf.CFDataGetBytePtr.restype = ctypes.c_void_p
    cf.CFRelease.argtypes = [ctypes.c_void_p]

    sl = ctypes.CDLL(SKYLIGHT)
    sl.CGSMainConnectionID.restype = ctypes.c_int
    sl.CGSSetWindowLevel.argtypes = [ctypes.c_int, ctypes.c_uint32, ctypes.c_int]
    sl.CGSSetWindowLevel.restype = ctypes.c_int
    sl.CGSGetWindowLevel.argtypes = [ctypes.c_int, ctypes.c_uint32, ctypes.POINTER(ctypes.c_int)]
    sl.CGSGetWindowLevel.restype = ctypes.c_int

    ax = ctypes.CDLL(APP_SERVICES)
    ax.AXIsProcessTrusted.restype = ctypes.c_ubyte  # Boolean is a single byte

    return cg, cf, sl, ax


CG, CF, SKY, AX = _load()


def display_bounds():
    r = CG.CGDisplayBounds(CG.CGMainDisplayID())
    return int(r.origin.x), int(r.origin.y), int(r.size.width), int(r.size.height)


def windows():
    """On-screen windows as dicts: number, pid, layer, bounds."""
    array = CG.CGWindowListCopyWindowInfo(1, 0)  # on-screen only, sorted front to back
    if not array:
        return []
    data = CF.CFPropertyListCreateData(None, ctypes.c_void_p(array), 100, 0, None)  # binary plist
    try:
        raw = ctypes.string_at(CF.CFDataGetBytePtr(data), CF.CFDataGetLength(data))
        info = plistlib.loads(raw)
    finally:
        CF.CFRelease(data)
        CF.CFRelease(ctypes.c_void_p(array))
    return [
        {
            "number": w.get("kCGWindowNumber"),
            "pid": w.get("kCGWindowOwnerPID"),
            "layer": w.get("kCGWindowLayer"),
            "bounds": dict(w.get("kCGWindowBounds") or {}),
        }
        for w in info
    ]


def pids_running(marker):
    """Pids whose command line contains marker, excluding this process."""
    out = subprocess.run(["ps", "-Ao", "pid=,command="], capture_output=True, text=True).stdout
    pids = set()
    for line in out.splitlines():
        pid, _, command = line.strip().partition(" ")
        if marker in command and pid.isdigit() and int(pid) != os.getpid():
            pids.add(int(pid))
    return pids


def find_windows(marker, timeout=0.0):
    """Normal-layer windows owned by a process running marker, polling until timeout."""
    deadline = time.time() + timeout
    while True:
        pids = pids_running(marker)
        found = [w for w in windows() if w["pid"] in pids and w["layer"] == 0]
        if found or time.time() >= deadline:
            return found
        time.sleep(0.2)


def window_level(number):
    """Effective level of a window, straight from the window server.

    CGWindowListCopyWindowInfo keeps reporting the level a window was created
    with, so it cannot confirm a change; CGSGetWindowLevel can.
    """
    level = ctypes.c_int()
    SKY.CGSGetWindowLevel(SKY.CGSMainConnectionID(), number, ctypes.byref(level))
    return level.value


def float_windows(marker, level=None, timeout=0.0, hold=False, interval=1.0):
    """Set the level on matching windows.

    The override lives as long as this process's window-server connection, and
    reverts when the process exits, so holding the pin means staying alive and
    re-asserting it until the window goes away.
    """
    level = CG.CGWindowLevelForKey(FLOATING_LEVEL_KEY) if level is None else level
    found = find_windows(marker, timeout)
    if not found:
        print(f"no window yet for {marker}")
        return 1

    conn = SKY.CGSMainConnectionID()
    first = True
    while True:
        for w in found:
            SKY.CGSSetWindowLevel(conn, w["number"], level)
        if first:
            report(found, level)
            first = False
        if not hold:
            return 0
        time.sleep(interval)
        found = find_windows(marker)
        if not found:
            print("reels window closed, releasing pin")
            return 0


def report(found, level):
    for w in found:
        now = window_level(w["number"])
        if now == level:
            print(f"pinned window {w['number']} at level {now}")
        elif not AX.AXIsProcessTrusted():
            print(f"window {w['number']} opened, but macOS only pins windows above other apps "
                  "for processes with Accessibility permission. Grant it to the app running "
                  "Claude Code: System Settings > Privacy & Security > Accessibility")
        else:
            print(f"window {w['number']} would not take level {level} (still {now})")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("display", help='print main display bounds as "x y w h"')

    p = sub.add_parser("float", help="pin matching windows above other windows")
    p.add_argument("--marker", required=True, help="text that appears in the owner's command line")
    p.add_argument("--level", type=int, default=None, help="CGWindowLevel (default: floating)")
    p.add_argument("--wait", type=float, default=0.0, help="seconds to wait for the window (default 0)")
    p.add_argument("--hold", action="store_true",
                   help="keep the pin asserted until the window closes (needs this process alive)")

    args = parser.parse_args()
    if args.cmd == "display":
        print(*display_bounds())
        return 0
    return float_windows(args.marker, args.level, args.wait, args.hold)


if __name__ == "__main__":
    sys.exit(main())
