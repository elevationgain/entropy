#!/usr/bin/env python3
"""Generate web/fixture.js: invented sample data in the exact /state payload shape.

Covers every state and card variant (question, plan, permission, running tool, todos,
priorities, PRs/ports, no-transcript agent, non-Claude agent). Nothing here is real.
Re-run after changing the payload shape in bin/entropy.
"""
import json, os, uuid

NOW = 1_790_000_000.0
M, H = 60, 3600
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rid = lambda: str(uuid.uuid4()).upper()


def agent(state, title, ws, repo, since, *, kind="claude", color=None, priority=None, account="default",
          model="claude-opus-5", effort="high", perm="auto", branch="main", changed=0, ahead=0, behind=0,
          you=None, reply=None, extra=None, transcript=True, group="Personal", prs=(), ports=(), unread=0,
          tool=None, turns=6, ctx=120_000, out=48_000, cpu=1, mem=160, note=None, files=(), commit="Tidy imports",
          description=None):
    sid, surf, wid = str(uuid.uuid4()), rid(), rid()
    t = None
    if transcript:
        t = {"ai_title": title, "model": model, "effort": effort, "permission_mode": perm, "mode": "normal",
             "git_branch": branch, "version": "2.1.280", "entrypoint": "cli", "turns": turns,
             "context_tokens": ctx, "output_tokens": out, "tool_errors": 1, "last_turn_ms": 42_000,
             "message_count": turns * 30, "last_user": you, "last_user_at": NOW - since - 3 * M,
             "last_prompt": you, "last_reply": reply, "last_assistant_at": NOW - since,
             "files_edited": len(files), "recent_files": list(files),
             "top_tools": [["Bash", 31], ["Edit", 12], ["Read", 9], ["Grep", 4]]}
        t.update(extra or {})
    return {
        "sid": sid, "state": state, "since": NOW - since, "last": NOW - since, "ws": ws, "wid": wid,
        "surface": surf, "title": title, "repo": repo, "kind": kind, "color": color,
        "cwd": f"/Users/dev/code/{repo}", "priority": priority,
        "detail": {
            "hook": {"last_hook": "PreToolUse" if state == "working" else "Stop", "tool": tool,
                     "tool_at": NOW - 40 if tool else None, "tool_calls": 57, "prompts": turns,
                     "turn_started": NOW - 3 * M if state == "working" else NOW - since - 3 * M,
                     "tool_errors": None, "subagents_done": 2},
            "session": {"pid": 40000 + len(title), "started_at": NOW - 5 * H, "account": account,
                        "transcript": f"/Users/dev/.claude/projects/-Users-dev-code-{repo}/{sid}.jsonl" if transcript else None},
            "proc": {"cpu": cpu, "rss_mb": mem, "etime": "05:00:00", "children": 1},
            "transcript": t,
            "workspace": {"description": description, "pinned": False, "group": group, "unread": unread, "window": 1,
                          "branch": branch, "dirty": bool(changed), "ports": list(ports), "prs": list(prs),
                          "latest_notification": note, "project_root": f"/Users/dev/code/{repo}", "remote": False},
            "git": {"branch": branch, "changed": changed, "ahead": ahead, "behind": behind,
                    "last_commit": commit, "last_commit_at": NOW - 2 * H},
            "notification": {"title": "Claude Code", "subtitle": f"Completed in {ws}", "body": note,
                             "created_at": "2026-09-23T17:00:00Z", "at": NOW - since, "read": False} if note else None,
        },
    }


groups = {
    "needs_input": [
        agent("needs_input", "Payments webhook retries", "Ledger", "ledger-api", 14 * M, color="#FF6B6B",
              priority={"level": "urgent", "reason": "Prod deploy blocked on your approval", "sticky": False, "set_at": NOW - 6 * M},
              group="Client A", account="work", branch="fix/webhook-retries", changed=3, ahead=2,
              you="Retries are double-charging on 502s. Find the cause and fix it before the 3pm deploy.",
              extra={"question": {"text": "The idempotency key is missing on the retry path. How should I backfill keys for the 1,204 in-flight webhooks?",
                                  "options": ["Derive from event id", "Generate new + dedupe table", "Skip backfill"], "more": 1},
                     "pending_tool": {"name": "AskUserQuestion", "summary": "The idempotency key is missing…"},
                     "todos": {"done": 4, "total": 6, "active": "Backfilling idempotency keys"}},
              prs=["https://github.com/acme/ledger-api/pull/412"], files=("retry.ts", "webhooks.ts")),
        agent("needs_input", "Onboarding copy refresh", "Website", "marketing-site", 31 * M, group="Personal",
              model="claude-sonnet-5", you="Rewrite the onboarding emails to be shorter and warmer.",
              extra={"plan": "## Plan\n1. Audit the 5 onboarding emails and their open rates\n2. Rewrite subject lines (A/B two variants each)\n3. Cut body copy ~40%, one CTA per email\n4. Update templates in /emails and preview locally",
                     "pending_tool": {"name": "ExitPlanMode", "summary": "## Plan 1. Audit the 5 onboarding emails…"}}),
        agent("needs_input", "Flaky e2e investigation", "Ledger", "ledger-web", 2 * M, color="#FF6B6B", group="Client A",
              account="work", branch="chore/e2e-flake", you="The checkout e2e test fails ~1 in 5 runs on CI. Figure out why.",
              extra={"pending_tool": {"name": "Bash", "summary": "docker compose -f ci/compose.yml up -d postgres && pnpm test:e2e --repeat-each=20 checkout.spec.ts"}}),
        agent("needs_input", "Docs site search", "Docs", "docs", 48 * M, group="Personal",
              you="Add search to the docs site.",
              reply="Search is wired up with a client-side index (38 KB gzipped). One decision for you: index the API reference too? It triples the index size.",
              note="Search is wired up with a client-side index (38 KB gzipped). One decision for you: index the API reference too?"),
    ],
    "working": [
        agent("working", "Migrate auth to OIDC", "Atlas", "atlas", 9 * M, color="#4C8DFF", tool="Edit",
              priority={"level": "high", "reason": "Security review Friday", "sticky": True, "set_at": NOW - 50 * M},
              group="Client B", account="work", branch="feat/oidc", changed=11, ahead=5, behind=1,
              you="Replace the session-cookie auth with OIDC. Keep the old path behind a flag for a week.",
              reply="Token refresh works end to end. Moving on to the admin routes.",
              extra={"pending_tool": {"name": "Edit", "summary": "middleware/auth.ts"},
                     "todos": {"done": 3, "total": 7, "active": "Porting admin routes to OIDC guards"}},
              files=("auth.ts", "session.ts", "oidc.ts", "flags.ts"), cpu=14, mem=410, ctx=182_000, out=121_000),
        agent("working", "Dashboard charts", "Nimbus", "nimbus", 4 * M, tool="Bash", group="Personal",
              model="claude-sonnet-5", effort="medium", branch="feat/charts", changed=6,
              you="Add the usage-over-time chart to the dashboard.",
              reply="Chart renders; running the visual regression suite now.",
              extra={"pending_tool": {"name": "Bash", "summary": "pnpm test:visual --update-snapshots=false"}},
              prs=["https://github.com/dev/nimbus/pull/88"], ports=(3000, 6006), cpu=62, mem=520),
    ],
    "idle": [
        agent("idle", "Release notes draft", "Nimbus", "nimbus", 2 * H,
              priority={"level": "low", "reason": "Whenever, before v2.4", "sticky": True, "set_at": NOW - 3 * H},
              you="Draft release notes for v2.4 from the merged PRs.",
              reply="Draft is in RELEASE_NOTES.md: 14 changes grouped into Features, Fixes, and Internal.",
              note="Draft is in RELEASE_NOTES.md: 14 changes grouped into Features, Fixes, and Internal."),
        agent("idle", "Claude Code", "Scratch", "scratch", 20 * H, transcript=False, group=None),
        agent("idle", "Refactor CLI flags", "Atlas", "atlas-cli", 40 * M, kind="codex", color="#4C8DFF",
              transcript=False, group="Client B", description="Internal CLI for the Atlas platform"),
    ],
    "ended": [
        agent("ended", "Dependency audit", "Ledger", "ledger-api", 5 * H, color="#FF6B6B", group="Client A",
              account="work", you="Audit dependencies for known CVEs.",
              reply="Done: bumped 9 packages, 2 need a major upgrade (tracked in #398)."),
    ],
}
payload = {"now": NOW, "workspaceCount": 7, "status": "", "windows": 2, "groups": groups,
           "totals": {k: len(v) for k, v in groups.items()}}
out = os.path.join(ROOT, "web", "fixture.js")
with open(out, "w") as fh:
    fh.write("// Generated by tools/make_fixture.py. Invented sample data in the /state shape.\n")
    fh.write("window.entropyFixture(" + json.dumps(payload, indent=1) + ");\n")
print("wrote", out)
