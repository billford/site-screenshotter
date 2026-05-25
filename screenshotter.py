#!/usr/bin/env python3
"""
site-screenshotter — headless screenshots of local or remote HTML pages.

Usage:
    python screenshotter.py                        # uses config.json in same dir
    python screenshotter.py --config myconf.json   # explicit config file
    python screenshotter.py docs/ --out shots/     # quick mode: screenshot every .html in a dir
"""

import argparse
import json
import sys
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None  # type: ignore[assignment]


def load_config(path: Path) -> dict:
    """Load and return a JSON config file, exiting with an error if missing or malformed."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"[screenshotter] Error loading config: {exc}", file=sys.stderr)
        sys.exit(1)


def pages_from_dir(html_dir: Path, out_dir: Path) -> list:
    """Return a page-list dict for every .html file found in html_dir."""
    return [
        {
            "url": p.as_uri(),
            "output": str(out_dir / p.with_suffix(".png").name),
        }
        for p in sorted(html_dir.glob("*.html"))
    ] if html_dir.is_dir() else []


def take_screenshots(pages: list, cfg: dict) -> None:
    """Render each page in a headless browser and save a PNG to the configured output path."""
    if sync_playwright is None:
        print("[screenshotter] playwright not installed. Run: pip install playwright && playwright install chromium")
        sys.exit(1)

    viewport_w = cfg.get("viewport_width", 1400)
    viewport_h = cfg.get("viewport_height", 900)
    settle_ms  = cfg.get("settle_ms", 1500)
    full_page  = cfg.get("full_page", True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": viewport_w, "height": viewport_h})

        for entry in pages:
            url     = entry["url"]
            out     = Path(entry["output"])
            out.parent.mkdir(parents=True, exist_ok=True)
            print(f"[screenshotter] {url}  →  {out}")
            page.goto(url, wait_until="networkidle")
            page.wait_for_timeout(settle_ms)
            page.screenshot(path=str(out), full_page=full_page)

        browser.close()

    print(f"[screenshotter] Done — {len(pages)} screenshot(s).")


def main() -> None:
    """Parse arguments and run in quick mode (directory) or config mode."""
    parser = argparse.ArgumentParser(description="Headless screenshots of HTML pages.")
    parser.add_argument("html_dir", nargs="?", help="Quick mode: directory of .html files")
    parser.add_argument("--config", default="config.json", help="Path to JSON config file")
    parser.add_argument("--out", default="screenshots", help="Output directory (quick mode)")
    args = parser.parse_args()

    if args.html_dir:
        html_dir = Path(args.html_dir)
        out_dir  = Path(args.out)
        pages = pages_from_dir(html_dir, out_dir)
        if not pages:
            print(f"[screenshotter] No .html files found in {html_dir}", file=sys.stderr)
            sys.exit(1)
        take_screenshots(pages, {})
    else:
        cfg = load_config(Path(args.config))
        pages = cfg.get("pages", [])
        if not pages:
            print("[screenshotter] No pages defined in config.", file=sys.stderr)
            sys.exit(1)
        take_screenshots(pages, cfg)


if __name__ == "__main__":
    main()
