"""Hermes event hook — cohermes shared-brain integration.

Fires on ``agent:start`` (Hermes discovers this from ~/.hermes/hooks/cohermes/).
Two side effects, wiring cohermes into Hermes's real agent lifecycle:

  1. **Subscription-auth preflight (A2)** — verify Claude Code will run on the
     developer's subscription, not metered API billing.
  2. **Orient / read-from-brain** — brief the agent from the shared Context Graph on
     the inbound task (relevant decisions + active learnings + architecture), so it
     starts aligned instead of re-deriving.

Requires cohermes importable in the Hermes process — set ``PYTHONPATH`` to the
cohermes repo root (see the recorded learning "MCP server needs PYTHONPATH=repo
root"). Hooks are side-effect only (Hermes discards their return), so the brief is
delivered by writing it to ``$HERMES_HOME/cohermes/brief-<session>.md`` and logging;
a production deploy would post it into the session. Deep prompt-injection (making
the brief part of the agent's context automatically) needs a change to Hermes's
context assembly — a separate, invasive step.
"""
import os
import pathlib

try:
    from cg import auth as _auth
    from cg import orient as _orient
    _READY, _ERR = True, ""
except Exception as e:  # noqa: BLE001
    _READY, _ERR = False, str(e)


async def handle(event_type: str, context: dict) -> None:
    if not _READY:
        print(f"[cohermes] hook idle — cg not importable ({_ERR}); "
              f"set PYTHONPATH to the cohermes repo root.", flush=True)
        return

    ctx = context or {}

    # 1) subscription-auth preflight (never blocks the pipeline; hooks are logged)
    try:
        a = _auth.preflight(strict=False)
        verdict = "OK subscription" if a.get("ok") else f"REVIEW ({a.get('mode')})"
        print(f"[cohermes] auth: {verdict}"
              + (f" · {a.get('subscription')}" if a.get("subscription") else ""), flush=True)
    except Exception as e:  # noqa: BLE001
        print(f"[cohermes] auth preflight error (non-fatal): {e}", flush=True)

    # 2) orient / read-from-brain on the inbound task
    task = str(ctx.get("message", "")).strip()
    if not task:
        return
    try:
        brief = _orient.brief(task)
    except Exception as e:  # noqa: BLE001
        print(f"[cohermes] orient error (non-fatal): {e}", flush=True)
        return

    home = pathlib.Path(os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes")))
    out_dir = home / "cohermes"
    out_dir.mkdir(parents=True, exist_ok=True)
    sid = str(ctx.get("session_id") or "session")
    (out_dir / f"brief-{sid}.md").write_text(brief)
    print(f"[cohermes] oriented on {task[:60]!r} → brief written "
          f"({len(brief)} chars) to {out_dir}/brief-{sid}.md", flush=True)
