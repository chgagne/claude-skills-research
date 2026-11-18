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
    s.add_argument("--force", action="store_true",
                   help="install: overwrite a differing service file")
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


def cmd_service(args):
    from dracmonlib import service

    if args.force and args.action != "install":
        print("dracmon service: --force only applies to install", file=sys.stderr)
        return 2
    if args.action == "install":
        return service.install(force=args.force)
    return getattr(service, args.action)()


def cmd_doctor(args):
    from dracmonlib import doctor
    from dracmonlib.config import load_config

    return doctor.run(load_config())


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.cmd == "capture":
        return cmd_capture(args)
    if args.cmd == "collect":
        return cmd_collect(args)
    if args.cmd == "service":
        return cmd_service(args)
    if args.cmd == "doctor":
        return cmd_doctor(args)
    return _not_implemented(args.cmd or "tui")


if __name__ == "__main__":
    sys.exit(main())
