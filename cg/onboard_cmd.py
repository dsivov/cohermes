"""cohermes · cg — the universal onboarder (``cohermes onboard``).

Non-destructive by construction: detect existing state and preserve it, wire the
project additively, and never write a metered key. Encodes the six traps once.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import requests

from cg import auth
from cg.project import ProjectConfig, save as save_project, default_workspace_for
from cg.runner import ensure_hermes_home

_TIMEOUT = 30


# ── working-agreement templates (the methodology the project inherits) ──
_WORKING_AGREEMENT = """\
# {title} — working agreement (auto-loaded each session)

This project's decision memory lives in **Context Graph** (workspace `{workspace}`),
reachable via your `context-graph` MCP tools. Follow three habits, in order:

1. **Query before you build.** Use `query_auto` / `search_precedents` /
   `get_entity_context` to check recorded decisions and existing modules first, and
   reuse the reasoning. A query that returns nothing is itself a finding — say so.
2. **Record the why, not the keystroke.** Capture rationale for choices worth keeping.
   If you can't say who decided it and why, it's telemetry, not memory — skip it.
3. **Use the governed moves.** Call `get_manifest` to discover this workspace's object
   types and governed actions, then `invoke_action` (or `record_decision`) — each is
   validated and audited. Do not invent parallel decision types; use what the manifest
   reports.

You run on the Claude **subscription**, never metered API billing.

Under the **Hermes-coordinator flavor** you run on a lightweight model and are NOT the
primary reasoner: delegate all substantive work — plans, architecture, design, decisions,
and code — to opus via the `ask_claude` tool, and do the CG interaction above (orient /
query precedent / record decisions) yourself. You have no file, terminal, or code tools;
when in doubt, call `ask_claude`. See `COORDINATOR.md` for the full role guide.
"""


def _cg(cfg: ProjectConfig, path: str):
    return requests.get(f"{cfg.cg_url.rstrip('/')}{path}",
                        headers={"LIGHTRAG-WORKSPACE": cfg.workspace}, timeout=_TIMEOUT)


def _ok(msg): print(f"  \033[32m✓\033[0m {msg}")
def _warn(msg): print(f"  \033[33m⚠\033[0m {msg}")
def _info(msg): print(f"  · {msg}")
def _step(n, msg): print(f"\n\033[36m[{n}]\033[0m {msg}")


# ── 1. preflight ──
def preflight(cfg: ProjectConfig) -> bool:
    _step("1/5", "Preflight")
    ok = True
    try:
        r = requests.get(f"{cfg.cg_url.rstrip('/')}/health", timeout=_TIMEOUT)
        _ok(f"Context Graph reachable at {cfg.cg_url} (HTTP {r.status_code})") if r.ok else _warn(f"CG returned HTTP {r.status_code}")
        ok = ok and r.ok
    except Exception as e:  # noqa: BLE001
        _warn(f"Context Graph not reachable at {cfg.cg_url}: {e}"); ok = False

    a = auth.auth_status()
    if a.get("mode") == "subscription":
        _ok(f"Claude subscription auth ({a.get('subscription','?')}) — A2 satisfied")
    else:
        _warn(f"Claude auth is '{a.get('mode')}', not a subscription — fix before running (A2)"); ok = False
    return ok


# ── 2. detect (preserve, don't clobber) ──
def detect(cfg: ProjectConfig) -> dict:
    _step("2/5", "Detect existing state (preserve, don't clobber)")
    state = {"ontology": None, "has_records": False, "mcp_json": None, "config": None}

    if (cfg.root / ".cohermes.yaml").exists():
        state["config"] = True; _info("existing .cohermes.yaml — will update in place")
    mcp = cfg.root / ".mcp.json"
    if mcp.exists():
        try:
            state["mcp_json"] = json.loads(mcp.read_text())
            servers = list(state["mcp_json"].get("mcpServers", {}).keys())
            _info(f"existing .mcp.json (servers: {servers or 'none'}) — will merge, not overwrite")
        except Exception:  # noqa: BLE001
            _warn(".mcp.json present but unparseable — leaving it untouched")

    try:
        r = _cg(cfg, "/ontology")
        if r.ok:
            o = (r.json() or {}).get("ontology", r.json())
            ots = o.get("object_types") or o.get("objectTypes") or []
            names = [t.get("name") if isinstance(t, dict) else t for t in ots]
            if names:
                state["ontology"] = names
                _ok(f"workspace '{cfg.workspace}' already has an ontology: {names}")
    except Exception:  # noqa: BLE001
        pass
    try:
        r = _cg(cfg, "/graph/label/list")
        if r.ok and isinstance(r.json(), list) and r.json():
            state["has_records"] = True
            _info(f"workspace has {len(r.json())} recorded labels — history will be preserved")
    except Exception:  # noqa: BLE001
        pass
    if not state["ontology"] and not state["has_records"]:
        _info(f"workspace '{cfg.workspace}' looks fresh")
    return state


# ── 3. CG-side ontology ──
def setup_ontology(cfg: ProjectConfig, state: dict) -> None:
    _step("3/5", f"Ontology (mode: {cfg.ontology})")
    if state["ontology"]:
        _ok("existing ontology preserved — not modified (detect-and-preserve)")
        return
    if cfg.ontology == "existing":
        _warn("ontology=existing but the workspace has none yet — nothing installed")
        return
    if cfg.ontology in ("team", "generate"):
        # P1: install the standard team ontology. Conversational generation is P2.
        if cfg.ontology == "generate":
            _info("conversational generation lands in P2 — installing the team ontology as a starting point")
        try:
            from cg import ontology as team
            r = requests.post(f"{cfg.cg_url.rstrip('/')}/ontology",
                              headers={"LIGHTRAG-WORKSPACE": cfg.workspace},
                              json={"ontology": team.ONTOLOGY}, timeout=_TIMEOUT)
            _ok("installed team ontology (Decision→Task→Commit→Review)") if r.ok else _warn(f"ontology install HTTP {r.status_code}: {r.text[:120]}")
        except Exception as e:  # noqa: BLE001
            _warn(f"could not install ontology: {e}")


# ── 4. client wiring (additive) ──
def wire(cfg: ProjectConfig) -> None:
    _step("4/5", "Client wiring (additive / merge)")
    save_project(cfg, cfg.root); _ok(".cohermes.yaml written")

    if "hermes" in cfg.flavors:
        ensure_hermes_home(cfg); _ok(".hermes/config.yaml — structured model + workspace-pinned CG MCP")
        _write_agreement(cfg, ".hermes.md")

    if "claude" in cfg.flavors:
        _merge_mcp_json(cfg)
        _write_agreement(cfg, "CLAUDE.md")

    _gitignore(cfg, ".hermes/")


def _write_agreement(cfg: ProjectConfig, name: str) -> None:
    path = cfg.root / name
    body = _WORKING_AGREEMENT.format(title=cfg.root.name, workspace=cfg.workspace)
    if path.exists():
        if "context-graph" in path.read_text() or "working agreement" in path.read_text():
            _info(f"{name} already carries a working agreement — left as-is")
            return
        _warn(f"{name} exists (not a cohermes agreement) — leaving it untouched")
        return
    path.write_text(body, encoding="utf-8"); _ok(f"{name} — working agreement")


def _merge_mcp_json(cfg: ProjectConfig) -> None:
    path = cfg.root / ".mcp.json"
    data = {"mcpServers": {}}
    if path.exists():
        try:
            data = json.loads(path.read_text())
        except Exception:  # noqa: BLE001
            _warn(".mcp.json unparseable — not touching it"); return
    servers = data.setdefault("mcpServers", {})
    if "context-graph" in servers:
        _info(".mcp.json already has context-graph — left as-is"); return
    servers["context-graph"] = {
        "type": "http", "url": f"{cfg.cg_url.rstrip('/')}/mcp",
        "headers": {"LIGHTRAG-WORKSPACE": cfg.workspace},
    }
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    _ok(".mcp.json — merged context-graph (Claude Code)")


def _gitignore(cfg: ProjectConfig, entry: str) -> None:
    gi = cfg.root / ".gitignore"
    lines = gi.read_text().splitlines() if gi.exists() else []
    if entry in lines:
        return
    with gi.open("a", encoding="utf-8") as fh:
        fh.write(("\n" if lines and lines[-1].strip() else "") +
                 f"\n# cohermes: project-local Hermes home\n{entry}\n")
    _ok(f".gitignore — {entry}")


# ── 5. verify ──
def verify(cfg: ProjectConfig) -> None:
    _step("5/5", "Verify (read-only)")
    try:
        r = _cg(cfg, "/ontology")
        _ok(f"workspace '{cfg.workspace}' reachable & wired (HTTP {r.status_code})") if r.ok else _warn(f"HTTP {r.status_code}")
    except Exception as e:  # noqa: BLE001
        _warn(f"verify failed: {e}")


def onboard(root: Path, cfg: ProjectConfig) -> int:
    print(f"\033[1mcohermes onboard\033[0m → {root}  (workspace: {cfg.workspace})")
    errs = cfg.validate()
    if errs:
        for e in errs:
            _warn(e)
        return 2
    if not preflight(cfg):
        _warn("preflight failed — fix the above and re-run (safe to re-run).")
        return 1
    state = detect(cfg)
    setup_ontology(cfg, state)
    wire(cfg)
    verify(cfg)
    print("\n\033[32mDone.\033[0m Next:")
    if "hermes" in cfg.flavors:
        print("  cohermes hermes            # Hermes runtime, pre-wired to the brain")
    if "claude" in cfg.flavors:
        print("  cohermes agent \"<task>\"     # Claude Code, pre-briefed")
    print("  cohermes doctor            # verify auth (A2), CG, model wiring")
    return 0
