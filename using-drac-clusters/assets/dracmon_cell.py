#!/usr/bin/env python3
"""Append cell events for dracmon from inside a job (Python >= 3.6, stdlib only).

Line format, one per event, appended to
$SCRATCH/.dracmon/cells/<campaign>/<jobid>[_<taskid>].log:

    epoch<TAB>jobid<TAB>event<TAB>cell<TAB>detail

Every function swallows all errors: a monitoring hook must never break a job.
cell() records any exception, including KeyboardInterrupt/SystemExit (e.g. scancel), as fail.
"""
import os
import re
import sys
import time
from contextlib import contextmanager

MAX_LINE = 511  # bytes, excluding the newline


def _clean(text):
    return str(text).replace("\t", " ").replace("\n", " ").replace("\r", " ")


def _safe_bytes(text):
    """Replace every byte outside [A-Za-z0-9._-] with '_' (byte-wise, like tr)."""
    return re.sub(rb"[^A-Za-z0-9._-]", b"_", str(text).encode("utf-8", "replace")).decode("ascii")


def _jobid():
    arr, task = os.environ.get("SLURM_ARRAY_JOB_ID"), os.environ.get("SLURM_ARRAY_TASK_ID")
    if arr and task:
        raw = arr + "_" + task
    else:
        raw = os.environ.get("SLURM_JOB_ID") or "local"
    return _safe_bytes(raw)


def _campaign():
    raw = os.environ.get("DRACMON_CAMPAIGN") or os.environ.get("SLURM_JOB_NAME") or "default"
    return _safe_bytes(raw)


def _emit(event, cell="", detail=""):
    try:
        scratch = os.environ.get("SCRATCH")
        if not scratch:
            return
        jobid = _jobid()
        directory = os.path.join(scratch, ".dracmon", "cells", _campaign())
        os.makedirs(directory, exist_ok=True)
        fields = [str(int(time.time())), jobid, event, _clean(cell), _clean(detail)]
        data = "\t".join(fields).encode("utf-8", "replace")[:MAX_LINE] + b"\n"
        fd = os.open(os.path.join(directory, jobid + ".log"),
                     os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
        try:
            os.write(fd, data)
        finally:
            os.close(fd)
    except Exception:
        pass


def plan(n):
    _emit("plan", "", n)


def start(cell):
    _emit("start", cell)


def done(cell):
    _emit("done", cell)


def fail(cell, reason=""):
    _emit("fail", cell, reason)


@contextmanager
def cell(name):
    start(name)
    try:
        yield
    except BaseException as exc:
        try:
            reason = "%s: %s" % (type(exc).__name__, exc)
        except Exception:
            reason = type(exc).__name__
        fail(name, reason)
        raise
    else:
        done(name)


def main(argv):
    try:
        event = argv[1] if len(argv) > 1 else ""
        arg = argv[2] if len(argv) > 2 else ""
        if event == "plan":
            _emit("plan", "", arg)
        elif event in ("start", "done"):
            _emit(event, arg)
        elif event == "fail":
            _emit("fail", arg, " ".join(argv[3:]))
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    main(sys.argv)
    sys.exit(0)
