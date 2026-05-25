"""Tests for screenshotter.py — config loading, directory scanning, and argument parsing."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import screenshotter


class TestLoadConfig(unittest.TestCase):
    def test_valid_json_returned_as_dict(self):
        cfg = {"viewport_width": 1400, "pages": []}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(cfg, f)
            tmp = Path(f.name)
        try:
            result = screenshotter.load_config(tmp)
            self.assertEqual(result["viewport_width"], 1400)
        finally:
            tmp.unlink(missing_ok=True)

    def test_missing_file_exits(self):
        with self.assertRaises(SystemExit):
            screenshotter.load_config(Path("/nonexistent/config.json"))

    def test_malformed_json_exits(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{not valid json")
            tmp = Path(f.name)
        try:
            with self.assertRaises(SystemExit):
                screenshotter.load_config(tmp)
        finally:
            tmp.unlink(missing_ok=True)


class TestPagesFromDir(unittest.TestCase):
    def test_html_files_become_pages(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            (tmp / "index.html").write_text("<html></html>")
            (tmp / "about.html").write_text("<html></html>")
            (tmp / "style.css").write_text("body {}")
            pages = screenshotter.pages_from_dir(tmp, Path("shots"), {})
        names = [Path(p["output"]).name for p in pages]
        self.assertIn("index.png", names)
        self.assertIn("about.png", names)
        self.assertNotIn("style.css", names)
        self.assertEqual(len(pages), 2)

    def test_empty_directory_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as d:
            pages = screenshotter.pages_from_dir(Path(d), Path("shots"), {})
        self.assertEqual(pages, [])

    def test_nonexistent_dir_returns_empty_list(self):
        pages = screenshotter.pages_from_dir(Path("/no/such/dir"), Path("shots"), {})
        self.assertEqual(pages, [])

    def test_output_path_uses_out_dir(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            (tmp / "dash.html").write_text("<html></html>")
            pages = screenshotter.pages_from_dir(tmp, Path("my_shots"), {})
        self.assertTrue(pages[0]["output"].startswith("my_shots"))

    def test_url_is_file_uri(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            (tmp / "index.html").write_text("<html></html>")
            pages = screenshotter.pages_from_dir(tmp, Path("shots"), {})
        self.assertTrue(pages[0]["url"].startswith("file://"))


class TestTakeScreenshots(unittest.TestCase):
    def _make_mock_playwright(self):
        mock_page = MagicMock()
        mock_browser = MagicMock()
        mock_browser.new_page.return_value = mock_page
        mock_chromium = MagicMock()
        mock_chromium.launch.return_value = mock_browser
        mock_pw = MagicMock()
        mock_pw.chromium = mock_chromium
        mock_sync_pw = MagicMock()
        mock_sync_pw.__enter__ = MagicMock(return_value=mock_pw)
        mock_sync_pw.__exit__ = MagicMock(return_value=False)
        return mock_sync_pw, mock_page

    def test_navigates_to_each_url(self):
        mock_sync_pw, mock_page = self._make_mock_playwright()
        pages = [
            {"url": "file:///tmp/a.html", "output": "/tmp/a.png"},
            {"url": "file:///tmp/b.html", "output": "/tmp/b.png"},
        ]
        with patch("screenshotter.sync_playwright", return_value=mock_sync_pw):
            screenshotter.take_screenshots(pages, {})
        calls = [c.args[0] for c in mock_page.goto.call_args_list]
        self.assertIn("file:///tmp/a.html", calls)
        self.assertIn("file:///tmp/b.html", calls)

    def test_screenshot_called_for_each_page(self):
        mock_sync_pw, mock_page = self._make_mock_playwright()
        pages = [{"url": "file:///tmp/x.html", "output": "/tmp/x.png"}]
        with patch("screenshotter.sync_playwright", return_value=mock_sync_pw):
            screenshotter.take_screenshots(pages, {})
        self.assertEqual(mock_page.screenshot.call_count, 1)

    def test_config_defaults_applied(self):
        mock_sync_pw, mock_page = self._make_mock_playwright()
        pages = [{"url": "file:///tmp/x.html", "output": "/tmp/x.png"}]
        with patch("screenshotter.sync_playwright", return_value=mock_sync_pw):
            screenshotter.take_screenshots(pages, {})
        _, kwargs = mock_page.screenshot.call_args
        self.assertTrue(kwargs.get("full_page", True))

    def test_no_playwright_exits(self):
        with patch("screenshotter.sync_playwright", None):
            with self.assertRaises(SystemExit):
                screenshotter.take_screenshots([{"url": "x", "output": "y"}], {})


class TestMainArgParsing(unittest.TestCase):
    def test_quick_mode_uses_html_dir(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            (tmp / "index.html").write_text("<html></html>")
            with patch("screenshotter.take_screenshots") as mock_take, \
                 patch("sys.argv", ["screenshotter.py", str(tmp)]):
                screenshotter.main()
            pages = mock_take.call_args[0][0]
            self.assertTrue(any("index.png" in p["output"] for p in pages))

    def test_quick_mode_empty_dir_exits(self):
        with tempfile.TemporaryDirectory() as d:
            with patch("sys.argv", ["screenshotter.py", d]):
                with self.assertRaises(SystemExit):
                    screenshotter.main()

    def test_config_mode_reads_file(self):
        cfg = {"pages": [{"url": "file:///x.html", "output": "x.png"}]}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(cfg, f)
            tmp = Path(f.name)
        try:
            with patch("screenshotter.take_screenshots") as mock_take, \
                 patch("sys.argv", ["screenshotter.py", "--config", str(tmp)]):
                screenshotter.main()
            pages = mock_take.call_args[0][0]
            self.assertEqual(pages[0]["url"], "file:///x.html")
        finally:
            tmp.unlink(missing_ok=True)

    def test_config_mode_no_pages_exits(self):
        cfg = {"pages": []}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(cfg, f)
            tmp = Path(f.name)
        try:
            with patch("sys.argv", ["screenshotter.py", "--config", str(tmp)]):
                with self.assertRaises(SystemExit):
                    screenshotter.main()
        finally:
            tmp.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
