#!/usr/bin/env python3
"""Read the account's 5-hour and 7-day utilisation, and wait until both are under a ceiling.

Every `claude -p --output-format stream-json` session emits a rate_limit_event carrying
unifiedWindows.five_hour.utilization and seven_day.utilization (0..1). A one-word Haiku
reply is the cheapest way to get a fresh reading.

  usage_gate.py --read                       # print the current utilisation
  usage_gate.py --five 0.40 --seven 0.75     # block until both are at or under the ceilings
"""
import argparse, json, subprocess, sys, time


def read_usage():
    p = subprocess.run(["claude", "-p", "--model", "claude-haiku-4-5-20251001", "--disable-slash-commands",
                        "--setting-sources", "", "--strict-mcp-config", "--no-session-persistence", "--tools=",
                        "--output-format", "stream-json", "--verbose", "Reply with OK."],
                       stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=300)
    five = seven = None
    for line in p.stdout.splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get("type") == "rate_limit_event":
            w = (e.get("rate_limit_info") or {}).get("unifiedWindows") or {}
            five = (w.get("five_hour") or {}).get("utilization", five)
            seven = (w.get("seven_day") or {}).get("utilization", seven)
    return five, seven


def wait_under(five_max, seven_max, poll=1200, log=print):
    while True:
        try:
            five, seven = read_usage()
        except Exception as exc:          # a failed probe is not a green light
            five = seven = None
            log(f"usage probe failed: {exc}")
        stamp = time.strftime("%H:%M")
        if five is not None and seven is not None and five <= five_max and seven <= seven_max:
            log(f"{stamp} usage 5h {five:.0%} 7d {seven:.0%}: go")
            return five, seven
        log(f"{stamp} usage 5h {five if five is None else f'{five:.0%}'} 7d "
            f"{seven if seven is None else f'{seven:.0%}'}: waiting {poll // 60} min")
        time.sleep(poll)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--read", action="store_true")
    ap.add_argument("--five", type=float, default=0.40); ap.add_argument("--seven", type=float, default=0.75)
    ap.add_argument("--poll", type=int, default=1200)
    a = ap.parse_args(argv)
    if a.read:
        print(json.dumps(dict(zip(("five_hour", "seven_day"), read_usage()))))
        return 0
    wait_under(a.five, a.seven, a.poll, log=lambda m: print(m, flush=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
