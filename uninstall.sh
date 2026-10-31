#!/usr/bin/env bash
# Remove the Ghost Shell hook and ~/.ghost-shell.
# ~/.ghost (history, graveyard, ofrenda) is left in place.
set -euo pipefail

line='source ~/.ghost-shell/ghost.sh'
for rc in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.bash_profile"; do
  [[ -f "$rc" ]] || continue
  tmp="$(mktemp)"
  grep -F -v "$line" "$rc" > "$tmp" || true
  mv "$tmp" "$rc"
  echo "Removed the hook from $rc"
done

rm -rf "$HOME/.ghost-shell"
echo "Ghost Shell has left. Your ofrenda in ~/.ghost was kept."
