# Roadmap

The HUD only helps while it's on screen. These close that gap: get to the waiting agent fast, hear
about it when you're elsewhere, and catch trouble before you open the card. Roughly value per effort.

## 1. Jump to next waiting

- Web: a key (`n`) jumps to the longest-waiting needs-you agent; pressing again cycles oldest → newest.
- CLI: `entropy next` does the same through the running server, so a global cmux shortcut can bind it
  and it works without the HUD visible.
- Reuses `/jump`. New piece is the ordering (needs_input by `since`, priority first) and a cycle index.

## 2. Alert when unfocused

- When the needs-you count rises and the HUD tab isn't focused (`document.hidden` / no focus): desktop
  notification (Notification API) and/or a short terminal beep. Off by default or a toggle in the header.
- The trigger already exists: `render()` glitches the mark on `needsNow > prevNeeds`.
- Notification click → jump to that agent.

## 3. Stuck / at-risk flags

Card badges from data already in `/state`:
- **Stalled**: working, no tool call (`hook.tool_at`) in N minutes.
- **Error spike**: `hook.tool_errors` climbing within the current turn.
- **Context high**: transcript context near the model's window, i.e. about to compact.

Thresholds as constants in `bin/entropy`; flags computed server-side so TUI and sidebar can show them.

## 4. Day in review — shipped (v1)

VIEW → DAY, served by `/day?date=YYYY-MM-DD` from transcripts on disk. Open questions from v1:
- "Waiting" is turn end → next prompt, so a parked session reads as a long wait. Separate blocked
  (agent asked you something) from parked?
- Permission prompts mid-turn count as working time.
- Claude transcripts only; no Codex.
- Link the "how agentic was my work today" query from 2026-09-23. TODO: where it lives.

## Also considered

- **Attention-debt decay** (novelty with a job): CRT flicker, mark glitches, and scanline drift scale
  with summed needs-you wait time. The page decays while agents wait and calms when the queue clears.
  Pairs with #2 as the peripheral-vision version of an alert.
- **Skipped: cost dashboards and charts.** Useful elsewhere; here they dilute "who needs me, right now."
