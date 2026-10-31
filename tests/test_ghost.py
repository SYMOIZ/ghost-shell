#!/usr/bin/env python3
"""Ghost Shell tests. Ollama is mocked; nothing is sent off the machine."""

import json
import os
import re
import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ghost  # noqa: E402


def _response(text):
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"message": {"content": text}}
    return response


def _plain(text):
    return re.sub(r"\033\[[0-9;]*m", "", text).replace("👻", "").replace("🪦", "").strip()


class GhostTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.env = patch.dict(os.environ, {"GHOST_DATA": self.tmp.name, "GHOST_PERSONA": "ghost"})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def test_whisper_prints_one_clamped_line(self):
        long_line = " ".join(f"w{i}" for i in range(25))
        with patch("ghost.requests.post", return_value=_response(long_line)) as post:
            buf = StringIO()
            with redirect_stdout(buf):
                code = ghost.main(["whisper", "make test", "2"])
        self.assertEqual(code, 0)
        out = buf.getvalue()
        self.assertIn("👻", out)
        self.assertIn(ghost.PURPLE, out)
        self.assertLessEqual(len(_plain(out).split()), 20)
        self.assertEqual(post.call_args.kwargs["timeout"], 5)
        body = post.call_args.kwargs["json"]
        self.assertEqual(body["model"], "gemma3:1b")
        self.assertIn("centuries-old ghost", body["messages"][0]["content"])
        self.assertTrue(post.call_args.args[0].startswith("http://localhost:11434/"))

    def test_whisper_is_silent_when_ollama_is_down(self):
        with patch("ghost.requests.post", side_effect=ConnectionError("down")):
            buf = StringIO()
            with redirect_stdout(buf):
                code = ghost.main(["whisper", "make test", "1"])
        self.assertEqual(code, 0)
        self.assertEqual(buf.getvalue(), "")

    def test_log_appends_history(self):
        code = ghost.main(["log", "git status", "0"])
        self.assertEqual(code, 0)
        text = Path(self.tmp.name, "history").read_text(encoding="utf-8")
        self.assertIn("\t0\tgit status\n", text)
        self.assertRegex(text, r"^\d{4}-\d{2}-\d{2}T")

    def test_deleted_targets(self):
        self.assertEqual(
            ghost.deleted_targets("rm -rf notes.txt draft.md"),
            ["notes.txt", "draft.md"],
        )
        self.assertEqual(ghost.deleted_targets("rmdir old"), ["old"])
        self.assertEqual(ghost.deleted_targets("sudo rm secrets.txt"), ["secrets.txt"])
        self.assertEqual(ghost.deleted_targets("git branch -D feature"), ["feature"])
        self.assertEqual(
            ghost.deleted_targets("git branch -D feature && rm old.txt"),
            ["feature", "old.txt"],
        )
        self.assertEqual(ghost.deleted_targets("ls -la"), [])
        self.assertEqual(ghost.deleted_targets("echo rm not-really"), [])
        self.assertEqual(ghost.deleted_targets("sudo"), [])

    def test_epitaph_writes_graveyard(self):
        epitaph = "Here lies the draft.\nIt never compiled, yet it rested."
        with patch("ghost.ask", return_value=epitaph):
            buf = StringIO()
            with redirect_stdout(buf):
                code = ghost.main(["epitaph", "rm -rf notes.txt"])
        self.assertEqual(code, 0)
        self.assertIn("🪦", buf.getvalue())
        self.assertIn(ghost.ORANGE, buf.getvalue())
        self.assertIn("Here lies the draft.", buf.getvalue())
        rows = ghost.load_graveyard()
        self.assertEqual(rows[0]["name"], "notes.txt")
        self.assertEqual(rows[0]["epitaph"], epitaph)
        self.assertRegex(rows[0]["date"], r"^\d{4}-\d{2}-\d{2}$")
        saved = json.loads(Path(self.tmp.name, "graveyard.jsonl").read_text(encoding="utf-8"))
        self.assertEqual(saved["name"], "notes.txt")

    def test_ofrenda_html(self):
        grave = Path(self.tmp.name, "graveyard.jsonl")
        grave.write_text(
            json.dumps({
                "name": "notes.txt",
                "date": "2026-10-31",
                "epitaph": "Here lies the draft.\nIt knew too much.",
            }) + "\n",
            encoding="utf-8",
        )
        with patch("ghost.webbrowser.open") as opener:
            buf = StringIO()
            with redirect_stdout(buf):
                code = ghost.main(["ofrenda"])
        self.assertEqual(code, 0)
        opener.assert_called_once()
        html = Path(self.tmp.name, "ofrenda.html").read_text(encoding="utf-8")
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("notes.txt", html)
        self.assertIn("2026-10-31", html)
        self.assertIn("Here lies the draft.", html)
        self.assertIn("flame", html)
        self.assertIn("@keyframes glow", html)


if __name__ == "__main__":
    unittest.main()
