#!/usr/bin/env bash
# Install Ghost Shell into ~/.ghost-shell and source it from the shell rc.
set -euo pipefail

cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo "ghost-shell: python3 is required" >&2
  exit 1
fi
if ! command -v ollama >/dev/null 2>&1; then
  echo "ghost-shell: ollama is required (https://ollama.com)" >&2
  exit 1
fi

if ! python3 -c "import requests" >/dev/null 2>&1; then
  python3 -m pip install --user -r requirements.txt
fi

echo "Pulling gemma3:1b (this stays on your machine)..."
ollama pull gemma3:1b

dest="$HOME/.ghost-shell"
mkdir -p "$dest"
cp ghost.py ghost.sh "$dest/"
rm -rf "$dest/personas" "$dest/templates"
cp -R personas "$dest/personas"
cp -R templates "$dest/templates"
chmod +x "$dest/ghost.py"

line='source ~/.ghost-shell/ghost.sh'
targets=()
[[ -f "$HOME/.bashrc" ]] && targets+=("$HOME/.bashrc")
[[ -f "$HOME/.zshrc" ]] && targets+=("$HOME/.zshrc")
if [[ ${#targets[@]} -eq 0 ]]; then
  case "${SHELL:-}" in
    */zsh) targets+=("$HOME/.zshrc") ;;
    *) targets+=("$HOME/.bashrc") ;;
  esac
fi

for rc in "${targets[@]}"; do
  touch "$rc"
  if grep -Fqx "$line" "$rc"; then
    echo "Already sourced in $rc"
  else
    printf '\n%s\n' "$line" >> "$rc"
    echo "Added the hook to $rc"
  fi
done

echo "Open a new terminal. The ghost is listening."
