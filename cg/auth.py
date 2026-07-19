"""cohermes · cg — subscription-auth preflight guard (A2).

Hard rule: cohermes agents must run Claude Code on a Pro/Max/Team **subscription**,
never metered API billing — in both tmux and ``claude -p`` modes. The footgun is a
stray ``ANTHROPIC_API_KEY`` (or a cloud-provider var) in the environment, which
silently outranks a logged-in subscription.

This guard (a) scrubs those variables from the environment cohermes uses to spawn
Claude Code, and (b) asserts the active auth mode via ``claude auth status`` before
any real work — failing fast rather than spending tokens.

Run:  python -m cg.auth        (report the current auth posture)
"""
import json
import os
import shutil
import subprocess

# Env vars that, if set, outrank subscription OAuth (precedence highest→lowest).
BILLING_ENV = [
    "ANTHROPIC_API_KEY",        # metered API billing — the main footgun
    "ANTHROPIC_AUTH_TOKEN",     # gateway bearer token
    "CLAUDE_CODE_USE_BEDROCK",
    "CLAUDE_CODE_USE_VERTEX",
    "CLAUDE_CODE_USE_FOUNDRY",
    "ANTHROPIC_BASE_URL",       # gateway/proxy redirect
]


def scrubbed_env(base: dict | None = None) -> tuple[dict, list[str]]:
    """A copy of the environment with every billing/override var removed.
    Use this env when spawning Claude Code so subscription OAuth wins."""
    env = dict(os.environ if base is None else base)
    removed = [k for k in BILLING_ENV if k in env]
    for k in BILLING_ENV:
        env.pop(k, None)
    return env, removed


def auth_status(env: dict | None = None) -> dict:
    """Query ``claude auth status`` and classify the active mode.
    Returns {available, mode in {subscription, api, none, unknown, None}, raw}.

    Real output is JSON, e.g. {"loggedIn": true, "authMethod": "claude.ai",
    "subscriptionType": "max", ...}; ``authMethod == "claude.ai"`` is subscription
    OAuth, anything else while logged in implies an API/console credential."""
    if shutil.which("claude") is None:
        return {"available": False, "mode": None, "raw": "claude CLI not found on PATH"}
    try:
        out = subprocess.run(["claude", "auth", "status"],
                             capture_output=True, text=True, timeout=30, env=env)
        raw = (out.stdout or out.stderr).strip()
    except Exception as e:  # noqa: BLE001 - report, don't crash the guard
        return {"available": True, "mode": None, "raw": f"error: {e}"}
    try:
        j = json.loads(raw)
        if not j.get("loggedIn"):
            mode = "none"
        elif j.get("authMethod") == "claude.ai":
            mode = "subscription"
        else:
            mode = "api"
        return {"available": True, "mode": mode, "raw": raw,
                "subscription": j.get("subscriptionType"), "email": j.get("email")}
    except json.JSONDecodeError:
        low = raw.lower()
        mode = "api" if ("api key" in low and "confirmed" in low) else (
            "subscription" if "subscription" in low else "unknown")
        return {"available": True, "mode": mode, "raw": raw}


def preflight(strict: bool = True) -> dict:
    """Scrub the env and assert subscription auth. In strict mode, raise
    SystemExit if Claude Code would use metered API billing."""
    env, removed = scrubbed_env()
    status = auth_status(env)
    result = {"scrubbed": removed, "ok": status["mode"] == "subscription", **status}
    if strict and status["available"] and status["mode"] == "api":
        raise SystemExit(
            "cohermes: refusing to run — Claude Code would use metered API billing, "
            "not your subscription. `unset ANTHROPIC_API_KEY` (and cloud-provider vars) "
            "and log in with `claude` / `claude setup-token`."
        )
    return result


if __name__ == "__main__":
    r = preflight(strict=False)
    print("scrubbed billing vars from spawn env:", r["scrubbed"] or "(none present)")
    print("claude CLI available:", r["available"])
    print("auth mode:", r["mode"])
    if r["available"]:
        sub = f" ({r.get('subscription')})" if r.get("subscription") else ""
        print("verdict:", f"OK — subscription{sub}" if r["ok"]
              else f"REVIEW — mode={r['mode']} (must be 'subscription')")
    else:
        print("verdict: cannot verify here (claude not installed on this box) —"
              " the guard runs on each developer's machine.")
