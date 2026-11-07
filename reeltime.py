"""Tracks how long Claude thinks per prompt (= reel time).
Usage: reeltime.py start | stop | report | selftest"""
import json, sys, time, datetime as dt
from pathlib import Path

D = Path(__file__).parent
START, LOG = D / "reeltime.start", D / "reeltime.jsonl"

def start():
    START.write_text(str(time.time()))

def stop():
    if not START.exists():
        return
    secs = time.time() - float(START.read_text())
    START.unlink()
    with LOG.open("a") as f:
        f.write(json.dumps({"day": dt.date.today().isoformat(), "secs": round(secs, 1)}) + "\n")

def fmt(s):
    m, s = divmod(int(s), 60)
    h, m = divmod(m, 60)
    return f"{h}h {m}m {s}s" if h else f"{m}m {s}s"

def summarize(rows, today):
    t = [r["secs"] for r in rows if r["day"] == today]
    a = [r["secs"] for r in rows]
    return (f"today: {len(t)} prompts, {fmt(sum(t))}\n"
            f"all time: {len(a)} prompts, {fmt(sum(a))}, longest {fmt(max(a, default=0))}")

def report():
    rows = [json.loads(l) for l in LOG.read_text().splitlines()] if LOG.exists() else []
    print(summarize(rows, dt.date.today().isoformat()))

def selftest():
    rows = [{"day": "d1", "secs": 60}, {"day": "d1", "secs": 90}, {"day": "d0", "secs": 3600}]
    out = summarize(rows, "d1")
    assert "today: 2 prompts, 2m 30s" in out and "longest 1h 0m 0s" in out, out
    print("ok")

if __name__ == "__main__":
    {"start": start, "stop": stop, "report": report, "selftest": selftest}[sys.argv[1]]()
