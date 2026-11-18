"""GPU counting from Slurm gres/TRES strings (stdlib only).

A whole GPU counts 1, a MIG slice ``<model>_<k>g.<mem>`` counts k/7, a shard
counts 1/shards_per_card[model] (1/4 when the model is unknown).
"""
from __future__ import annotations

import re

_PAREN = re.compile(r"\([^)]*\)")
_MIG = re.compile(r"_(\d)g\.")
UNKNOWN_SHARD_FRACTION = 0.25


def _items(gres: str):
    """Yield (kind, model or None, count) for each gpu/shard entry of a gres or
    TRES string. Accepts ``gres/gpu:h100=4``, ``gres/gpu=4``, ``gres/gpu:h100:4``,
    ``gres:gpu:1``, ``gpu:l40s:4(S:0-1)``; other entries and garbage are skipped."""
    for raw in _PAREN.sub("", gres or "").split(","):
        item = raw.strip()
        for prefix in ("gres/", "gres:"):
            if item.startswith(prefix):
                item = item[len(prefix):]
                break
        if "=" in item:
            key, _, num = item.partition("=")
            kind, _, model = key.partition(":")
        else:
            parts = item.split(":")
            if len(parts) < 2:
                continue
            kind, num = parts[0], parts[-1]
            model = ":".join(parts[1:-1])
            try:
                float(num)
            except ValueError:  # typed entry with no count: gres/gpu:h100 means 1
                num, model = "1", ":".join(parts[1:])
        if kind not in ("gpu", "shard"):
            continue
        try:
            n = float(num)
        except ValueError:
            continue
        yield kind, (model or None), n


def shards_per_card(partitions) -> dict[str, int]:
    """{model: shards per card} from partition gres such as
    ``gpu:l40s:4,shard:l40s:16`` (-> {"l40s": 4})."""
    out: dict[str, int] = {}
    for p in partitions:
        gpus: dict[str, float] = {}
        shards: dict[str, float] = {}
        for kind, model, n in _items(p.gres):
            if model is None:
                continue
            d = gpus if kind == "gpu" else shards
            d[model] = d.get(model, 0) + n
        for model, s in shards.items():
            g = gpus.get(model)
            if g and s and model not in out:
                out[model] = max(1, round(s / g))
    return out


def _gpu_value(model: str | None, n: float) -> float:
    if model:
        m = _MIG.search(model)
        if m:
            return n * int(m.group(1)) / 7
    return n


def gpu_count(tres: str, shards: dict[str, int]) -> float:
    """GPUs held by a job, from squeue %b or sacct AllocTRES. A typed entry
    (``gres/gpu:h100=4``) and its untyped total (``gres/gpu=4``) are the same
    GPUs: typed entries win and the untyped one is used only when no typed
    entry exists. Never raises; unparseable input counts 0."""
    typed = {"gpu": [], "shard": []}
    untyped = {"gpu": [], "shard": []}
    for kind, model, n in _items(tres):
        (typed if model else untyped)[kind].append((model, n))
    total = 0.0
    for model, n in typed["gpu"] or untyped["gpu"]:
        total += _gpu_value(model, n)
    for model, n in typed["shard"] or untyped["shard"]:
        per = shards.get(model) if model else None
        total += n / per if per else n * UNKNOWN_SHARD_FRACTION
    return total
