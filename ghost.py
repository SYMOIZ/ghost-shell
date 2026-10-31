#!/usr/bin/env python3
"""Ghost Shell — a local Ollama ghost for the terminal.

History and the graveyard stay in ~/.ghost. If Ollama is down, commands
print nothing and exit 0 so the shell never breaks.
"""

import json
import os
import shlex
import sys
import time
import webbrowser
from datetime import datetime
from pathlib import Path

import requests

OLLAMA = "http://localhost:11434"
TIMEOUT = 5
PURPLE = "\033[2;38;5;103m"  # dim gray-purple
ORANGE = "\033[38;5;214m"  # marigold
RESET = "\033[0m"
SEPS = {"&&", "||", "|", ";"}
WRAPPERS = {"sudo", "command", "time", "nohup"}
SAMPLES = (
    "git status",
    "rm -rf dist/",
    "pytest -q",
    "curl https://example.com",
    "docker compose up",
)
ROOT = Path(__file__).resolve().parent
USAGE = "usage: ghost.py whisper|log|seance|epitaph|graveyard|ofrenda|bench ..."
FALLBACK_PERSONA = (
    "You are a centuries-old ghost haunting this terminal. "
    "React to the command in one eerie, darkly funny sentence. "
    "Never explain. Never use more than 20 words."
)


def data_dir():
    """~/.ghost, or GHOST_DATA when a test needs a scratch folder."""
    override = os.environ.get("GHOST_DATA")
    return Path(override) if override else Path.home() / ".ghost"


def model_name():
    return os.environ.get("GHOST_MODEL", "gemma3:1b")


def persona_text():
    """System prompt. GHOST_PERSONA selects personas/<name>.txt."""
    name = os.environ.get("GHOST_PERSONA", "ghost")
    path = ROOT / "personas" / f"{name}.txt"
    if path.is_file():
        return path.read_text(encoding="utf-8").strip()
    return FALLBACK_PERSONA


def clamp_words(text, limit):
    return " ".join(text.replace("\n", " ").split()[:limit])


def emit(text):
    print(text, flush=True)


def ask(system, user, model=None):
    """One /api/chat call. Raises if Ollama is down; callers stay silent."""
    response = requests.post(
        f"{OLLAMA}/api/chat",
        json={
            "model": model or model_name(),
            "stream": False,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        },
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    message = response.json().get("message") or {}
    return (message.get("content") or "").strip()


def _folder():
    folder = data_dir()
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def cmd_log(command, exit_code):
    stamp = datetime.now().astimezone().isoformat(timespec="seconds")
    safe = command.replace("\n", " ").replace("\t", " ")
    with (_folder() / "history").open("a", encoding="utf-8") as handle:
        handle.write(f"{stamp}\t{exit_code}\t{safe}\n")


def recent_history(limit=50):
    path = data_dir() / "history"
    if not path.is_file():
        return ""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[-limit:])


def cmd_whisper(command, exit_code):
    heard = f"The user ran: {command}\nExit code: {exit_code}"
    line = clamp_words(ask(persona_text(), heard), 20)
    if line:
        emit(f"👻 {PURPLE}{line}{RESET}")


def cmd_seance(question):
    system = (
        persona_text()
        + "\nUsing only the history, answer in character. "
        "Two or three spooky sentences. Do not invent commands."
    )
    log = recent_history() or "(the history book is empty)"
    line = clamp_words(ask(system, f"History:\n{log}\n\nQuestion: {question}"), 80)
    if line:
        emit(f"👻 {PURPLE}{line}{RESET}")


def _operands(tokens, start):
    names, index = [], start
    while index < len(tokens) and tokens[index] not in SEPS:
        if not tokens[index].startswith("-"):
            names.append(tokens[index])
        index += 1
    return names, index


def deleted_targets(command):
    """Names destroyed by rm, rmdir, or `git branch -D`."""
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        tokens = command.split()
    found, index = [], 0
    while index < len(tokens):
        if tokens[index] in SEPS:
            index += 1
            continue
        while index < len(tokens) and tokens[index] in WRAPPERS:
            index += 1
        if index >= len(tokens):
            break
        if tokens[index] in SEPS:
            continue
        base = os.path.basename(tokens[index])
        if base in ("rm", "rmdir"):
            names, index = _operands(tokens, index + 1)
            found.extend(names)
            continue
        end = index + 1
        while end < len(tokens) and tokens[end] not in SEPS:
            end += 1
        window = tokens[index + 1 : end]
        if base == "git" and window[:1] == ["branch"] and "-D" in window:
            names, _ = _operands(window, window.index("-D") + 1)
            found.extend(names)
        index = end
    return found


def cmd_epitaph(command):
    targets = deleted_targets(command)
    if not targets:
        return
    system = (
        persona_text()
        + "\nWrite a two-line epitaph for something just deleted. "
        "Darkly funny, in the spirit of a Día de los Muertos ofrenda. "
        "Output exactly two short lines and nothing else."
    )
    today = datetime.now().astimezone().strftime("%Y-%m-%d")
    with (_folder() / "graveyard.jsonl").open("a", encoding="utf-8") as handle:
        for name in targets:
            try:
                text = ask(system, f"Deleted: {name}")
            except Exception:
                continue
            lines = [part.strip() for part in text.splitlines() if part.strip()]
            epitaph = "\n".join(lines[:2]) or clamp_words(text, 24)
            if not epitaph:
                continue
            record = {"name": name, "date": today, "epitaph": epitaph}
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            body = epitaph.replace("\n", "\n   ")
            emit(f"🪦 {ORANGE}{name}\n   {body}{RESET}")


def load_graveyard():
    path = data_dir() / "graveyard.jsonl"
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def cmd_graveyard():
    rows = load_graveyard()
    if not rows:
        emit(f"🪦 {ORANGE}The graveyard is still empty.{RESET}")
        return
    for row in rows:
        emit(f"🪦 {ORANGE}{row.get('name', '?')}  ({row.get('date', '')}){RESET}")
        for line in str(row.get("epitaph", "")).splitlines():
            emit(f"   {ORANGE}{line}{RESET}")


def _esc(value):
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_ofrenda(rows):
    """Drop each burial into templates/ofrenda.html as a candle."""
    if not rows:
        candles = '<p class="empty">No one is buried yet. The candles are unlit.</p>'
    else:
        candles = "\n".join(
            '<article class="candle"><div class="flame"></div><div class="wax"></div>'
            f"<h2>{_esc(row.get('name', '?'))}</h2>"
            f"<time>{_esc(row.get('date', ''))}</time>"
            f"<p>{_esc(row.get('epitaph', '')).replace(chr(10), '<br>')}</p></article>"
            for row in rows
        )
    template = (ROOT / "templates" / "ofrenda.html").read_text(encoding="utf-8")
    return template.replace("<!--CANDLES-->", candles)


def cmd_ofrenda():
    path = _folder() / "ofrenda.html"
    path.write_text(render_ofrenda(load_graveyard()), encoding="utf-8")
    emit(str(path))
    try:
        webbrowser.open(path.resolve().as_uri())
    except Exception:
        pass


def cmd_bench():
    raw = os.environ.get("GHOST_BENCH_MODELS", model_name())
    models = [part.strip() for part in raw.split(",") if part.strip()]
    system = persona_text()
    emit("| Model | Avg latency |")
    emit("| --- | --- |")
    for name in models:
        times = []
        for sample in SAMPLES:
            start = time.perf_counter()
            try:
                ask(system, f"The user ran: {sample}\nExit code: 0", name)
            except Exception:
                continue
            times.append(time.perf_counter() - start)
        cell = f"{sum(times) / len(times):.2f}s" if times else "n/a"
        emit(f"| {name} | {cell} |")


def dispatch(cmd, args):
    if cmd == "whisper" and len(args) >= 2:
        cmd_whisper(args[0], args[1])
    elif cmd == "log" and len(args) >= 2:
        cmd_log(args[0], args[1])
    elif cmd == "seance" and args:
        cmd_seance(" ".join(args))
    elif cmd == "epitaph" and args:
        cmd_epitaph(" ".join(args))
    elif cmd == "graveyard":
        cmd_graveyard()
    elif cmd == "ofrenda":
        cmd_ofrenda()
    elif cmd == "bench":
        cmd_bench()
    else:
        emit(USAGE)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        emit(USAGE)
        return 0
    # A dead model, a missing file, a bad history line: never break the shell.
    try:
        dispatch(argv[0], argv[1:])
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
