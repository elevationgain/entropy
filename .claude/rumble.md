# Rumble config

Read by the Rumble test writer, implementer, reviewer and
`/rumble:implement`. Keep it short: point at the project's existing docs
instead of restating them.

Rules added by `/rumble:retro` carry a `<!-- from #<N> -->` comment
pointing at the merged PR whose retro prompted them. Keep those comments.

## Base branch

main

## Branching and PRs

`<type>/<short-description>` off main. Squash merge. Commit messages: short
imperative subject, no prefix convention (see `git log`).

## Gate

Must pass before every review and before handoff:

```
python3 -m py_compile bin/entropy && python3 -m unittest discover -s tests -t . && python3 tools/make_fixture.py
```

## Extra layers

| Command | Run when | Needs |
|---|---|---|
| `bin/entropy serve` then `cmux browser --surface <ref> screenshot --out <png>` on the HUD tab (`/?fixture`) | `web/index.html` changes | cmux running |

## Testing strategy

Source: `CLAUDE.md`

- New or changed server logic in `bin/entropy` ships with `unittest` tests in the same diff
- Tests import `bin/entropy` via `importlib` (it has no `.py` extension) and use synthetic files in a temp dir, never `~/.claude`
- Bug fixes start with a failing test
- `web/index.html` changes are verified by a screenshot against `/?fixture`, not unit tests

## Test layout

- Unit: `tests/test_*.py` (stdlib `unittest` only)

## Review focus

- `bin/entropy` stays a single stdlib-only file
- No new agent states; overlays only, per CLAUDE.md
- `/state` carries prompt/reply text: nothing binds beyond localhost, nothing new leaks real paths into `web/fixture.js`
- Incremental file tailing (`fold_new_lines`) stays incremental: no re-reading whole transcripts per tick

## Never

- Read real `~/.claude` transcripts from tests or commit data derived from them
- Add pip/npm dependencies
