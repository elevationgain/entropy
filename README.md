# Entropy

One view of every coding agent running across all your [cmux](https://cmux.com) windows: what needs you, what's working, what's idle. Click a card to jump to that agent's terminal.

cmux custom sidebars only see the window they're in. Entropy builds its state from cmux's app-wide socket instead, so a single page covers everything. You can put it in its own window on a second monitor.

## Install

```sh
git clone git@github.com:elevationgain/entropy.git ~/Projects/Entropy
~/Projects/Entropy/install.sh
entropy window
```

The installer symlinks `bin/entropy` into `~/.local/bin` and `sidebar/entropy.js` into `~/.config/cmux/sidebars`. Run `./install.sh --uninstall` to remove the links.

Requirements: macOS, cmux, and `python3` (standard library only). Claude sessions launched in cmux report state automatically; other agents need `cmux hooks setup`. `git` and `ps` are optional; they add detail to the cards.

## Use

| Command | What it does |
|---|---|
| `entropy` / `entropy serve` | Web HUD at http://127.0.0.1:7878. `--port`, `--host 0.0.0.0` for LAN (no auth). |
| `entropy window` | New cmux window with a server tab and a browser tab on the HUD. |
| `entropy priority <urgent\|high\|low\|normal> [reason]` | Flag the calling agent's session for attention (see below). |
| `entropy tui` | Terminal version. `j`/`k`, Enter to jump, `e` toggles ended, `q` quits. |
| `cmux right-sidebar set custom entropy` | In-window sidebar version (this window's agents only). |

The page has Board/List layouts and Full/Compact density. Both settings are remembered per browser.

## Priority

Agents (or you) can flag a session for attention at runtime:

```sh
entropy priority urgent "prod deploy blocked on your approval"
entropy priority low "long refactor, no rush"
entropy priority normal            # clear
```

Run it inside an agent's terminal and it targets that session automatically, using `$CLAUDE_CODE_SESSION_ID` or `$CMUX_SURFACE_ID`. From elsewhere, pass `--session` or `--surface`. Flagged cards sort to the top of their column: urgent gets a red outline, high gets a badge, low sinks and dims. A flag clears when you next prompt that session, because it has your attention; `--sticky` keeps it. Flags are stored in `~/.local/state/entropy/priorities.json`.

## How it works

| Source | Gives |
|---|---|
| `cmux events --category agent --category feed` | Live hook events, replayed since cmux started. This drives each agent's state. |
| `cmux sessions --json` | Sessions older than the event buffer: pid, account (session dir), transcript path. |
| `cmux rpc mobile.workspace.list` | Every window's workspaces and tabs (titles, groups, colors, unread). |
| `cmux rpc extension.sidebar.snapshot` (per window) | Branch, ports, PR URLs, latest notification. |
| `cmux rpc notification.list` | Notification text for each terminal. |
| Claude transcript JSONL | Title, prompts and replies, pending tool, question or plan, todos, model, tokens, files edited. |
| `ps`, `git status` | CPU and memory; ahead/behind, changed files, last commit. |

State rules copy cmux's own (`AgentChatSessionRegistry+Lifecycle.swift`):

| Event | State |
|---|---|
| SessionStart, Stop | idle |
| Prompt submitted, tool used | working |
| Permission request, question, plan ready, notification | needs you |
| SessionEnd | ended |

HTTP endpoints: `GET /` (the page, re-read on every request), `GET /state` (JSON snapshot), `GET /stream` (SSE), `POST /jump {wid, surface}`, `POST /priority {session|surface, level, reason, sticky}`.

## Develop

- `web/index.html` holds the whole UI. Edit it and reload the tab; no restart needed.
- `bin/entropy` holds the engine and server. Restart `entropy serve` after changes.
- `curl -s localhost:7878/state | jq` shows the real payload the page renders.

**Roadmap:** cmux `main` has `cmux rpc current.list`, which returns agent state across all windows. Once a release ships it, it replaces the rebuilt state logic.
