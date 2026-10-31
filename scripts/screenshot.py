#!/usr/bin/env python3
"""Headless screenshots of the ofrenda and the landing page.

Usage: GHOST_DATA=/tmp/ghost-demo python scripts/screenshot.py
"""

import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def ofrenda_path():
    data = os.environ.get("GHOST_DATA")
    if not data:
        sys.exit("Set GHOST_DATA to the folder that holds ofrenda.html")
    path = Path(data) / "ofrenda.html"
    if not path.is_file():
        sys.exit(f"Missing {path}. Run: ghost.py ofrenda --no-open")
    return path


def shoot(page, path, width, height, clip=None):
    page.set_viewport_size({"width": width, "height": height})
    page.wait_for_timeout(2000)
    page.screenshot(path=str(path), full_page=False, clip=clip)


def main():
    ofrenda = ofrenda_path()
    landing = DOCS / "index.html"
    DOCS.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        page.goto(ofrenda.resolve().as_uri())
        page.wait_for_timeout(2000)
        page.screenshot(path=str(DOCS / "ofrenda.png"), full_page=False)

        # DEV cover is the altar itself, at 1000x420, with every epitaph inside the frame.
        page.set_viewport_size({"width": 1000, "height": 420})
        page.add_style_tag(content="""
          h1, main > p, .picado { display: none; }
          body { min-height: 420px; height: 420px; display: flex; align-items: center; justify-content: center; }
          main { flex: none; display: block; width: 100%; max-width: none; padding: 8px 10px; }
          .altar { margin: 0; gap: 8px 10px; }
          .candle { width: 230px; }
          .flame { height: 18px; }
          .wax { height: 32px; }
        """)
        page.wait_for_timeout(2000)
        page.screenshot(path=str(DOCS / "ofrenda-cover.png"), full_page=False)

        page.set_viewport_size({"width": 1280, "height": 720})
        page.goto(landing.resolve().as_uri())
        page.wait_for_timeout(2600)
        page.screenshot(path=str(DOCS / "landing.png"), full_page=False)
        browser.close()
    print(DOCS / "ofrenda.png")
    print(DOCS / "ofrenda-cover.png")
    print(DOCS / "landing.png")


if __name__ == "__main__":
    main()
