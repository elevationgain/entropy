#!/usr/bin/env bash
# Symlink entropy into place. Safe to re-run; `./install.sh --uninstall` reverses it.
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname "$0")" && pwd)"
BIN_DIR="${ENTROPY_BIN_DIR:-$HOME/.local/bin}"
SIDEBAR_DIR="$HOME/.config/cmux/sidebars"

links=(
  "$ROOT/bin/entropy:$BIN_DIR/entropy"
  "$ROOT/sidebar/entropy.js:$SIDEBAR_DIR/entropy.js"
)

if [[ "${1:-}" == "--uninstall" ]]; then
  for pair in "${links[@]}"; do
    dst="${pair#*:}"
    [[ -L "$dst" ]] && rm "$dst" && echo "removed $dst"
  done
  exit 0
fi

command -v cmux >/dev/null || { echo "cmux not found on PATH (install cmux first)"; exit 1; }
command -v python3 >/dev/null || { echo "python3 not found"; exit 1; }

mkdir -p "$BIN_DIR" "$SIDEBAR_DIR"
for pair in "${links[@]}"; do
  src="${pair%%:*}" dst="${pair#*:}"
  if [[ -e "$dst" && ! -L "$dst" ]]; then
    echo "skip $dst: exists and is not a symlink (move it aside and re-run)"
    continue
  fi
  ln -sfn "$src" "$dst"
  echo "linked $dst -> $src"
done

case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *) echo "note: $BIN_DIR is not on PATH" ;;
esac

# Claude's hooks are injected by the cmux wrapper; other agents need `cmux hooks setup`.

echo "done. try: entropy window"
