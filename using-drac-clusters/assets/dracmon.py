#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["textual==8.2.8"]
# ///
# Textual pin: 8.2.8 (latest release at least two weeks old on 2026-11-17).
"""dracmon: terminal monitor for DRAC Slurm clusters."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def _not_implemented(name):
    print(f"dracmon {name}: not implemented", file=sys.stderr)
    return 2


def build_parser():
    p = argparse.ArgumentParser(prog="dracmon", description=__doc__)
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("tui", help="interactive monitor (default)")
    c = sub.add_parser("collect", help="poll the clusters")
    c.add_argument("--once", action="store_true", help="one cycle, then exit")
    s = sub.add_parser("service", help="manage the background collector")
    s.add_argument("action", choices=["install", "uninstall", "status"])
    sub.add_parser("doctor", help="check the setup")
    cap = sub.add_parser("capture", help="capture raw cluster output as fixtures")
    cap.add_argument("clusters", nargs="+", metavar="CLUSTER")
    cap.add_argument("--out", required=True, metavar="DIR")
    return p


def cmd_capture(args):
    from dracmonlib import capture
    from dracmonlib.config import load_config

    cfg = load_config()
    known = {c.name: c for c in cfg.clusters}
    unknown = [n for n in args.clusters if n not in known]
    if unknown:
        print(f"dracmon capture: unknown cluster(s): {' '.join(unknown)} "
              f"(known: {' '.join(known)})", file=sys.stderr)
        return 2
    clusters = [known[n] for n in dict.fromkeys(args.clusters)]
    written = capture.capture(clusters, Path(args.out), timeout=max(cfg.ssh_timeout, 120))
    for p in written:
        print(p)
    return 0 if len(written) == len(clusters) else 1


def cmd_collect(args):
    from dracmonlib import collector
    from dracmonlib.config import load_config

    return collector.collect(load_config(), args.once)


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.cmd == "capture":
        return cmd_capture(args)
    if args.cmd == "collect":
        return cmd_collect(args)
    return _not_implemented(args.cmd or "tui")


if __name__ == "__main__":
    sys.exit(main())
