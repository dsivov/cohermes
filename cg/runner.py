"""cohermes · cg — run the two flavors from a project's ``.cohermes.yaml``.

Both flavors run on the Claude subscription (A2), pin the project's CG workspace,
and never depend on a scratchpad install. This is the generalization of the
hand-written ``cg/hermes`` + ``cg/cohermes-agent`` launchers.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import yaml

from cg.project import ProjectConfig

# A2: env that would silently route to metered billing — scrubbed on every run.
_METERED_ENV = (
    "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN",
    "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY",
)


def base_env(cfg: ProjectConfig) -> dict:
    env = os.environ.copy()
    for k in _METERED_ENV:
        env.pop(k, None)
    env["COHERMES_CG_URL"] = cfg.cg_url
    env["COHERMES_CG_WORKSPACE"] = cfg.workspace   # kills the amnesia trap
    if cfg.developer:
        env["COHERMES_DEVELOPER"] = cfg.developer
    return env


def cohermes_home() -> Path:
    """The durable cohermes checkout (this package's repo root)."""
    return Path(__file__).resolve().parent.parent


def _bin(name: str) -> str:
    """A console script next to the running interpreter (durable venv)."""
    cand = Path(sys.executable).parent / name
    return str(cand) if cand.exists() else name


def ensure_hermes_home(cfg: ProjectConfig) -> bool:
    """Write/repair the project-local Hermes home config (structured model +
    workspace-pinned context-graph MCP). Idempotent; returns True if changed."""
    home = cfg.hermes_home
    home.mkdir(parents=True, exist_ok=True)
    cfgfile = home / "config.yaml"
    data = {}
    if cfgfile.exists():
        data = yaml.safe_load(cfgfile.read_text(encoding="utf-8")) or {}

    changed = False
    if data.get("model") != cfg.model:            # structured → subscription, not Bedrock
        data["model"] = cfg.model
        changed = True
    want = {"url": f"{cfg.cg_url.rstrip('/')}/mcp",
            "headers": {"LIGHTRAG-WORKSPACE": cfg.workspace}}
    servers = data.setdefault("mcp_servers", {})
    if servers.get("context-graph") != want:
        servers["context-graph"] = want
        changed = True

    if changed:
        cfgfile.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return changed


def run_hermes(cfg: ProjectConfig, args: list[str]) -> int:
    """The Hermes runtime flavor — its own agent loop, on the subscription model."""
    if "hermes" not in cfg.flavors:
        print("[cohermes] the 'hermes' flavor is not enabled in .cohermes.yaml", file=sys.stderr)
        return 2
    ensure_hermes_home(cfg)
    env = base_env(cfg)
    env["HERMES_HOME"] = str(cfg.hermes_home)      # project-local, isolated
    cmd = [_bin("hermes")] + (args or ["chat"])
    return subprocess.run(cmd, env=env, cwd=str(cfg.root)).returncode


def run_agent(cfg: ProjectConfig, task: str | None,
              print_mode: bool, passthrough: list[str]) -> int:
    """The Claude Code flavor — pre-briefed from the shared brain (cg.run)."""
    if "claude" not in cfg.flavors:
        print("[cohermes] the 'claude' flavor is not enabled in .cohermes.yaml", file=sys.stderr)
        return 2
    env = base_env(cfg)
    env["PYTHONPATH"] = f"{cohermes_home()}{os.pathsep}{env.get('PYTHONPATH','')}".rstrip(os.pathsep)
    cmd = [sys.executable, "-m", "cg.run"]
    if print_mode:
        cmd.append("-p")
    if task:
        cmd.append(task)
    if passthrough:
        cmd += ["--", *passthrough]
    return subprocess.run(cmd, env=env, cwd=str(cfg.root)).returncode
