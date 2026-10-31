# Ghost Shell

A haunted terminal for Hacktoberfest's **Ghost in the Machine** challenge. After you run a command, a local open-weight model (Gemma, through [Ollama](https://ollama.com)) whispers one eerie line. On Día de los Muertos it keeps an ofrenda for everything you delete.

The model runs on your machine. Command history and the names of deleted files never leave it.

![Ghost Shell demo](docs/demo.gif)

> Demo GIF placeholder. Record a terminal session and save it as `docs/demo.gif`.

## Install

Three commands:

```bash
git clone https://github.com//ghost-shell.git
cd ghost-shell
./install.sh
```

`install.sh` checks for `python3` and `ollama`, pulls `gemma3:1b`, copies the project to `~/.ghost-shell/`, and adds this line once to your bash or zsh rc file:

```bash
source ~/.ghost-shell/ghost.sh
```

Open a new terminal. Uninstall with `./uninstall.sh` (your `~/.ghost` history and graveyard are kept).

Requires Python 3.9+ and the `requests` library. Nothing else.

## Usage

```bash
make test
# 👻 the tests died screaming, and the makefile took notes

rm abandoned.md
# 🪦 abandoned.md
#    Here lies a draft that almost mattered.
#    The candle remembers the unsaved lines.

ghost seance "what did I do last night?"
# 👻 You summoned three builds and buried a branch named experiment.

ghost graveyard          # list every buried name and its epitaph
ghost ofrenda            # write ~/.ghost/ofrenda.html and open it
ghost off                # silence the hook
ghost on                 # wake it again
GHOST_BENCH_MODELS="gemma3:1b,gemma3:4b" ghost bench
```

Whispers show up on about one command in three, and on every non-zero exit. `cd`, `ls`, `clear`, and `ghost` stay quiet. Deletions (`rm`, `rmdir`, `git branch -D`) always get an epitaph, written in the background so the prompt does not wait.

### Voices

`GHOST_PERSONA` picks a file in `personas/`. No code change.

| Persona | File |
| --- | --- |
| `ghost` (default) | `personas/ghost.txt` |
| `victorian` | `personas/victorian.txt` |
| `cobol-spirit` | `personas/cobol-spirit.txt` |
| `pirate` | `personas/pirate.txt` |

```bash
export GHOST_MODEL=gemma3:1b          # any local Ollama tag
export GHOST_PERSONA=pirate
```

## Why open-source matters

- **It works offline.** After the model is pulled, Ollama is only contacted at `http://localhost:11434`.
- **Your history stays home.** `~/.ghost/history` and the deleted names in `~/.ghost/graveyard.jsonl` are never uploaded.
- **It is free.** The shell hook, the personas, and the page are MIT licensed. Gemma is an open-weight model.
- **You can swap the brain.** `GHOST_MODEL` changes the model. `GHOST_PERSONA` changes the voice. Both are files and environment variables, not a fork.

## Architecture

```
~/.bashrc or ~/.zshrc
        |
        |  source ~/.ghost-shell/ghost.sh
        v
    ghost.sh
        |
        |-- log (synchronous, local file only)
        |         |
        |         v
        |   ~/.ghost/history
        |
        |-- whisper  (background, ~1 in 3, always on errors)
        |-- epitaph  (background, only for rm / rmdir / git branch -D)
        |         |
        |         v
        |     ghost.py ---- HTTP ----> Ollama 127.0.0.1:11434
        |         |                      model: $GHOST_MODEL (gemma3:1b)
        |         |                      voice: personas/$GHOST_PERSONA.txt
        |         v
        |   ~/.ghost/graveyard.jsonl
        |
        +-- ghost ofrenda --> ~/.ghost/ofrenda.html
```

If Ollama is down, the Python side prints nothing and exits 0. The hook never waits on it.

## Benchmarks

Placeholder from a machine that has not been measured yet. Fill it in with `ghost bench`.

| Model | Avg latency |
| --- | --- |
| gemma3:1b | — |
| gemma3:4b | — |

`ghost bench` sends the same five sample commands to each tag in `GHOST_BENCH_MODELS` and prints average latency. Five seconds is the cap on any single call.

## GitHub Pages

The landing page is `docs/index.html` (HTML and CSS only). `docs/CNAME` is a placeholder (`your-domain.example.com`). Delete that file if you want the default `*.github.io` site. Replace it with your domain if you have one.

## Tests

```bash
python3 -m pip install -r requirements.txt
python3 -m unittest discover -s tests -v
```
