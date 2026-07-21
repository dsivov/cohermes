"""cohermes · cg — project configuration (``.cohermes.yaml``) and discovery.

A project onboarded to cohermes carries a small, committed ``.cohermes.yaml`` that
makes it self-describing: which CG workspace holds its memory, which model to run
on the subscription, which run flavors are enabled. The durable ``cohermes`` command
reads it and does the right thing — no per-project scripts.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

CONFIG_NAME = ".cohermes.yaml"

# A2 / trap-fixes baked into the defaults:
#  - model is the STRUCTURED, CONCRETE form → routes to the anthropic Messages
#    (subscription) endpoint; a bare "claude-code" would fall back to metered Bedrock.
DEFAULT_MODEL = {"provider": "anthropic", "default": "claude-opus-4-8"}
DEFAULT_CG_URL = "http://localhost:9621"
ONTOLOGY_MODES = ("generate", "existing", "team")
FLAVORS = ("hermes", "claude")


@dataclass
class ProjectConfig:
    workspace: str
    cg_url: str = DEFAULT_CG_URL
    model: dict = field(default_factory=lambda: dict(DEFAULT_MODEL))
    ontology: str = "generate"
    flavors: list = field(default_factory=lambda: list(FLAVORS))
    developer: str | None = None
    root: Path = field(default=None, repr=False)  # the project dir; not serialized

    @property
    def hermes_home(self) -> Path:
        return self.root / ".hermes"

    def to_dict(self) -> dict:
        return {
            "workspace": self.workspace,
            "cg_url": self.cg_url,
            "model": self.model,
            "ontology": self.ontology,
            "flavors": self.flavors,
            **({"developer": self.developer} if self.developer else {}),
        }

    def validate(self) -> list[str]:
        errs = []
        if not self.workspace or not all(c.isalnum() or c == "_" for c in self.workspace):
            errs.append(f"workspace {self.workspace!r} must be [A-Za-z0-9_]")
        if self.ontology not in ONTOLOGY_MODES:
            errs.append(f"ontology must be one of {ONTOLOGY_MODES}, got {self.ontology!r}")
        if not isinstance(self.model, dict) or "provider" not in self.model or "default" not in self.model:
            errs.append("model must be {provider, default} — a bare string routes to metered Bedrock")
        bad = [f for f in self.flavors if f not in FLAVORS]
        if bad:
            errs.append(f"unknown flavors {bad}; allowed {FLAVORS}")
        return errs


def find_config(start: Path | None = None) -> Path | None:
    """Walk up from *start* (default cwd) to find a ``.cohermes.yaml``."""
    d = (start or Path.cwd()).resolve()
    for cur in (d, *d.parents):
        candidate = cur / CONFIG_NAME
        if candidate.is_file():
            return candidate
    return None


def load(start: Path | None = None) -> ProjectConfig:
    path = find_config(start)
    if not path:
        raise FileNotFoundError(
            f"no {CONFIG_NAME} found from {start or Path.cwd()} upward — run `cohermes onboard` first")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    root = path.parent
    cfg = ProjectConfig(
        workspace=data.get("workspace", ""),
        cg_url=data.get("cg_url", DEFAULT_CG_URL),
        model=data.get("model") or dict(DEFAULT_MODEL),
        ontology=data.get("ontology", "generate"),
        flavors=data.get("flavors") or list(FLAVORS),
        developer=data.get("developer"),
        root=root,
    )
    return cfg


def save(cfg: ProjectConfig, root: Path | None = None) -> Path:
    root = root or cfg.root or Path.cwd()
    path = root / CONFIG_NAME
    header = (
        "# cohermes project config — committed so this repo is self-describing.\n"
        "# `cohermes onboard` writes it; `cohermes hermes|agent|doctor` read it.\n"
    )
    path.write_text(header + yaml.safe_dump(cfg.to_dict(), sort_keys=False), encoding="utf-8")
    return path


def default_workspace_for(root: Path) -> str:
    """A sane default workspace name derived from the project dir."""
    name = root.resolve().name
    return "".join(c if (c.isalnum() or c == "_") else "_" for c in name).strip("_") or "project"
