# site-screenshotter

Headless screenshots of local or remote HTML pages, using Playwright + Chromium. Drop it into any static site project to keep README images current.

## Install

```bash
pip install playwright
playwright install chromium
```

## Usage

### Quick mode — screenshot every `.html` file in a directory

```bash
python screenshotter.py docs/
# → writes screenshots/<page>.png for each file
```

```bash
python screenshotter.py docs/ --out shots/
# → writes shots/<page>.png
```

### Config mode — explicit pages with custom output paths

```bash
python screenshotter.py                        # reads config.json
python screenshotter.py --config myconf.json   # explicit config
```

`config.json`:

```json
{
  "viewport_width": 1400,
  "viewport_height": 900,
  "settle_ms": 1500,
  "full_page": true,
  "pages": [
    {
      "url": "file:///path/to/docs/index.html",
      "output": "screenshots/index.png"
    },
    {
      "url": "https://example.com",
      "output": "screenshots/example.png"
    }
  ]
}
```

### Config options

| Key | Default | Description |
|-----|---------|-------------|
| `viewport_width` | `1400` | Browser window width in px |
| `viewport_height` | `900` | Browser window height in px |
| `settle_ms` | `1500` | Wait after page load (ms) — gives JS charts time to render |
| `full_page` | `true` | Capture full scrollable page height |

## Wiring into a build script

```bash
# At the end of your build_and_push.sh:
python screenshotter.py --config screenshotter.json
git add screenshots/
git diff --cached --quiet || git commit -m "screenshots: update"
```

## How it works

Playwright drives a headless Chromium instance. `wait_until="networkidle"` ensures the page has finished loading, then `settle_ms` gives client-side chart libraries (Chart.js, D3, etc.) time to finish rendering before the screenshot is taken. Both `file://` and `http://` URLs work.
