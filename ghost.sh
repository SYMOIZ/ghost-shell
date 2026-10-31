# Ghost Shell hook. Source this from ~/.bashrc or ~/.zshrc.
# Logging is synchronous and tiny. The model runs in the background
# so a slow or dead Ollama can never delay the prompt.
# Every failure is ignored. This file must not break the shell.

[[ -n "${_GHOST_LOADED:-}" ]] && return 0
_GHOST_LOADED=1

if [[ -n "${BASH_VERSION:-}" ]]; then
  _GHOST_SRC="${BASH_SOURCE[0]}"
elif [[ -n "${ZSH_VERSION:-}" ]]; then
  # eval keeps this zsh-only expansion from being a bash syntax error.
  eval '_GHOST_SRC="${(%):-%x}"'
else
  _GHOST_SRC="$HOME/.ghost-shell/ghost.sh"
fi
# `||` so a bad path cannot abort the user's shell under `set -e`.
_GHOST_HOME="$(cd "$(dirname "$_GHOST_SRC")" 2>/dev/null && pwd)" || _GHOST_HOME="$HOME/.ghost-shell"
_GHOST_PY="$_GHOST_HOME/ghost.py"

# ghost seance "..." | graveyard | ofrenda | on | off | bench
ghost() {
  case "${1:-}" in
    on)  export GHOST_ENABLED=1; return 0 ;;
    off) export GHOST_ENABLED=0; return 0 ;;
    seance)
      shift
      command python3 "$_GHOST_PY" seance "$*" || true
      ;;
    graveyard|ofrenda|bench)
      command python3 "$_GHOST_PY" "$1" || true
      ;;
    *)
      command python3 "$_GHOST_PY" "$@" || true
      ;;
  esac
}

_ghost_trivial() {
  local base="${1%% *}"
  base="${base##*/}"
  case "$base" in
    cd|ls|clear|ghost) return 0 ;;
  esac
  return 1
}

# rm, rmdir, or `git branch -D`, including after sudo or a separator.
_ghost_is_deletion() {
  printf '%s\n' "$1" | grep -Eq \
    '(^|[;&|(])[[:space:]]*(sudo[[:space:]]+)?(rm|rmdir)([[:space:]]|$)|git[[:space:]]+branch[[:space:]]+-D'
}

_ghost_split_hist() {
  local hist="$1"
  hist="${hist#"${hist%%[![:space:]]*}"}"
  _GHOST_NUM="${hist%% *}"
  _GHOST_CMD="${hist#"$_GHOST_NUM"}"
  _GHOST_CMD="${_GHOST_CMD#"${_GHOST_CMD%%[![:space:]]*}"}"
}

_ghost_record() {
  local status="$1"
  local cmd="$2"
  [[ "${GHOST_ENABLED:-1}" == "0" || -z "$cmd" ]] && return 0
  case "$cmd" in
    *ghost.py*) return 0 ;;
  esac
  command python3 "$_GHOST_PY" log "$cmd" "$status" >/dev/null 2>&1 || true
  _ghost_trivial "$cmd" && return 0
  # Subshell, ignored SIGHUP, background: the prompt never waits on Ollama.
  if _ghost_is_deletion "$cmd"; then
    (trap '' HUP; command python3 "$_GHOST_PY" epitaph "$cmd" 2>/dev/null &)
  fi
  if [[ "$status" != "0" ]] || (( RANDOM % 3 == 0 )); then
    (trap '' HUP; command python3 "$_GHOST_PY" whisper "$cmd" "$status" 2>/dev/null &)
  fi
  return 0
}

_ghost_bash_hook() {
  local status=$?
  local hist
  hist=$(HISTTIMEFORMAT= history 1 2>/dev/null || true)
  if [[ -n "$hist" ]]; then
    _ghost_split_hist "$hist"
    if [[ -n "${_GHOST_NUM}" && "${_GHOST_NUM}" != "${_GHOST_HISTNUM:-}" ]]; then
      _GHOST_HISTNUM="$_GHOST_NUM"
      _ghost_record "$status" "$_GHOST_CMD" || true
    fi
  fi
  return "$status"
}

_ghost_zsh_hook() {
  local status=$?
  local hist
  hist=$(fc -l -1 2>/dev/null || true)
  if [[ -n "$hist" ]]; then
    _ghost_split_hist "$hist"
    if [[ -n "${_GHOST_NUM}" && "${_GHOST_NUM}" != "${_GHOST_HISTNUM:-}" ]]; then
      _GHOST_HISTNUM="$_GHOST_NUM"
      _ghost_record "$status" "$_GHOST_CMD" || true
    fi
  fi
  return "$status"
}

if [[ -n "${BASH_VERSION:-}" ]]; then
  hist=$(HISTTIMEFORMAT= history 1 2>/dev/null || true)
  [[ -n "$hist" ]] && _ghost_split_hist "$hist" && _GHOST_HISTNUM="$_GHOST_NUM"
  if [[ "$(declare -p PROMPT_COMMAND 2>/dev/null || true)" == declare\ -a* ]]; then
    PROMPT_COMMAND=("_ghost_bash_hook" "${PROMPT_COMMAND[@]}")
  else
    PROMPT_COMMAND="_ghost_bash_hook${PROMPT_COMMAND:+;$PROMPT_COMMAND}"
  fi
elif [[ -n "${ZSH_VERSION:-}" ]]; then
  hist=$(fc -l -1 2>/dev/null || true)
  [[ -n "$hist" ]] && _ghost_split_hist "$hist" && _GHOST_HISTNUM="$_GHOST_NUM"
  autoload -Uz add-zsh-hook 2>/dev/null || true
  add-zsh-hook precmd _ghost_zsh_hook 2>/dev/null || true
fi
unset hist
