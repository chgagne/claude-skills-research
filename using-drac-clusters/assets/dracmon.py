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


def main(argv=None):
    args = build_parser().parse_args(argv)
    return _not_implemented(args.cmd or "tui")


if __name__ == "__main__":
    sys.exit(main())
