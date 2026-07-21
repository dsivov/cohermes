"""cohermes-agent — launch a Claude Code agent pre-briefed from the shared brain.

The clean way to start an agent aligned with the team. Before handing off to Claude
Code it:
  1. runs the A2 subscription-auth preflight (hard-stops on metered API billing);
  2. fetches the orient briefing for the task from the shared Context Graph;
  3. launches Claude Code with that brief injected via ``--append-system-prompt`` —
     so the agent begins with the team's decisions + learnings *automatically*, no
     tool call, no lookup.

This is the launch-layer counterpart to the Hermes ``agent:start`` hook, and it
sidesteps the "hooks can't inject prompt context" limit without touching Hermes
internals.

    cohermes-agent                                       # project-level interactive session
    cohermes-agent "add a gitlab review source"          # interactive, oriented on that topic
    cohermes-agent -p "how should we test a connector?"  # one-shot print mode
"""
import argparse
import subprocess
import sys

from cg import auth, config, orient

# When no task/topic is given (a project-level interactive start), orient broadly.
DEFAULT_TOPIC = "current project state: recent decisions, active priorities, and architecture"


def launch(task: str | None = None, print_mode: bool = False,
           passthrough: list[str] | None = None) -> int:
    # 1) auth gate (A2) — refuse metered API billing
    a = auth.preflight(strict=True)
    sub = f" ({a.get('subscription')})" if a.get("subscription") else ""
    print(f"[cohermes-agent] auth OK — subscription{sub}", file=sys.stderr)

    # 2) orient from the shared brain (on the given topic, or a broad project brief)
    topic = task or DEFAULT_TOPIC
    print(f"[cohermes-agent] orienting on {topic!r} in workspace '{config.WORKSPACE}' …",
          file=sys.stderr)
    brief = orient.brief(topic)

    # 3) launch Claude Code with the brief injected at the system-prompt layer
    cmd = ["claude"]
    if print_mode:
        cmd += ["-p", task]
    cmd += ["--append-system-prompt", brief]
    cmd += (passthrough or [])
    print(f"[cohermes-agent] launching Claude Code, pre-briefed ({len(brief)} chars).",
          file=sys.stderr)
    return subprocess.run(cmd).returncode


def main():
    ap = argparse.ArgumentParser(
        description="Launch a Claude Code agent pre-briefed from the shared brain.")
    ap.add_argument("task", nargs="?", default=None,
                    help="task/topic to orient on; omit for a project-level interactive session")
    ap.add_argument("-p", "--print", action="store_true", dest="print_mode",
                    help="one-shot print mode (claude -p) — requires a task")
    ap.add_argument("claude_args", nargs=argparse.REMAINDER,
                    help="extra args passed through to claude (after --)")
    args = ap.parse_args()
    if args.print_mode and not args.task:
        ap.error("-p/--print needs a task (the prompt to run one-shot)")
    extra = [a for a in args.claude_args if a != "--"]
    raise SystemExit(launch(args.task, args.print_mode, extra))


if __name__ == "__main__":
    main()
