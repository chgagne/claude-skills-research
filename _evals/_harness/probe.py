#!/usr/bin/env python3
"""Memory probe: the bare model, with no tools and no skill, answers each prompt N times.

Used before freezing a case set, to tell what the model can do from memory alone.
Each prompts/<case>.txt is run --runs times; outputs land in <out>/<case>_r<k>.txt.

  probe.py --prompts probes/prompts --out probes/round1 --runs 3 --jobs 6
"""
import argparse, concurrent.futures as cf, pathlib, subprocess, sys

# --tools= (with the equals sign): --tools and --allowedTools are variadic and swallow
# a following positional prompt, which then waits on stdin forever.
CMD = ["claude", "-p", "--disable-slash-commands", "--setting-sources", "",
       "--strict-mcp-config", "--no-session-persistence", "--tools="]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--prompts", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--model", default="claude-opus-5-5")
    ap.add_argument("--timeout", type=int, default=1500)
    a = ap.parse_args(argv)
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    jobs = [(p, k) for k in range(1, a.runs + 1) for p in sorted(pathlib.Path(a.prompts).glob("*.txt"))]

    def run(job):
        p, k = job
        r = subprocess.run(CMD + ["--model", a.model, p.read_text()], stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, timeout=a.timeout)
        (out / f"{p.stem}_r{k}.txt").write_text(r.stdout + ("\nSTDERR:" + r.stderr if r.returncode else ""))
        return p.stem, k, r.returncode

    with cf.ThreadPoolExecutor(a.jobs) as ex:
        for res in ex.map(run, jobs):
            print(*res, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
