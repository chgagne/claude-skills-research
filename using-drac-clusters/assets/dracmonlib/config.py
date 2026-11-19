"""Configuration loading for dracmon (stdlib only)."""
from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_CLUSTERS = ["narval", "rorqual", "fir", "nibi", "trillium", "tamia", "killarney", "vulcan"]
DEFAULT_CADENCE = {"queue": 300, "cells": 300, "accounting": 900,
                   "usage": 3600, "disk": 3600, "partitions": 3600}


@dataclass
class Cluster:
    name: str
    host: str
    pinned: bool = False


@dataclass
class GlobCampaign:
    campaign: str
    cluster: str
    done_glob: str
    total: int


@dataclass
class Config:
    clusters: list[Cluster] = field(default_factory=lambda: [Cluster(n, n) for n in DEFAULT_CLUSTERS])
    cadence: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_CADENCE))
    idle_release: int = 7200
    released_check: int = 3600  # deprecated, unused: a released cluster gets no command
    ssh_timeout: int = 60
    cells_retention_days: int = 30
    retention_days: int = 90
    usage_retention_days: int = 365
    status_page: int = 900
    glob_campaigns: list[GlobCampaign] = field(default_factory=list)


_SCALARS = ("idle_release", "released_check", "ssh_timeout", "cells_retention_days",
            "retention_days", "usage_retention_days", "status_page")
_TABLES = ("cadence", "cluster", "glob_campaign")


def _xdg(var: str, fallback: str) -> Path:
    v = os.environ.get(var)
    return Path(v) if v else Path.home() / fallback


def state_dir() -> Path:
    d = _xdg("XDG_STATE_HOME", ".local/state") / "dracmon"
    d.mkdir(parents=True, exist_ok=True)
    return d


def config_path() -> Path:
    return _xdg("XDG_CONFIG_HOME", ".config") / "dracmon" / "config.toml"


def _check_keys(where: str, got: dict, allowed) -> None:
    for k in got:
        if k not in allowed:
            raise ValueError(f"unknown config key {k!r} in {where}")


def load_config(path: Path | None = None) -> Config:
    cfg = Config()
    path = Path(path) if path is not None else config_path()
    if not path.exists():
        return cfg
    with open(path, "rb") as f:
        data = tomllib.load(f)
    _check_keys("top level", data, _SCALARS + _TABLES)
    for k in _SCALARS:
        if k in data:
            setattr(cfg, k, int(data[k]))
    cad = data.get("cadence", {})
    _check_keys("[cadence]", cad, DEFAULT_CADENCE)
    cfg.cadence.update({k: int(v) for k, v in cad.items()})
    if "cluster" in data:
        cl = []
        for c in data["cluster"]:
            _check_keys("[[cluster]]", c, ("name", "host", "pinned"))
            if "name" not in c:
                raise ValueError("[[cluster]] entry missing 'name'")
            cl.append(Cluster(c["name"], c.get("host", c["name"]), bool(c.get("pinned", False))))
        cfg.clusters = cl
    gcs = []
    for g in data.get("glob_campaign", []):
        _check_keys("[[glob_campaign]]", g, ("campaign", "cluster", "done_glob", "total"))
        for req in ("campaign", "cluster", "done_glob", "total"):
            if req not in g:
                raise ValueError(f"[[glob_campaign]] entry missing {req!r}")
        gcs.append(GlobCampaign(g["campaign"], g["cluster"], g["done_glob"], int(g["total"])))
    cfg.glob_campaigns = gcs
    return cfg
