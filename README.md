# Article Extractor (Newspaper3k + Chrome Extension)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE) [![Release](https://img.shields.io/github/v/release/HeyAvijitRoy/ArticleExtractor?include_prereleases\&label=Release)](https://github.com/HeyAvijitRoy/ArticleExtractor/releases/tag/v2.0.0)

Extract clean sentences (or a DataFrame) from news articles with one click — right from your browser. Overlays, popups, image captions, and "Editors’ Picks" are stripped automatically.

---

## What’s new

* **Robust extractor pipeline**: Trafilatura → Readability-lxml → Newspaper3k (fallback)
* **Modal/overlay filtering**: removes popups, cookie banners, sidebars, captions, and non-article blocks before parsing
* **Smarter sentence splitting**: fixes cases like `Italy.Mr.` and `”Mr.` so titles don’t break lines
* **DataFrame export**: download **CSV** (with UTF‑8 BOM for Excel) or **Excel** (`.xlsx`)
* **ASCII Clean** option: convert curly quotes/em‑dashes to straight ASCII for spreadsheets or downstream tools

---

## Project Overview

Chrome Extension + local Flask server that extracts article content and returns **sentences**. All processing runs **locally** on your machine.

**Highlights**

* One‑click extraction from any article page
* NLP-grade sentence tokenization (NLTK `punkt`)
* Resilient to paywall clutter/overlays and side modules
* Multiple export formats: JSON / CSV / Excel

---

## Requirements

* **Python 3.8+** (3.10/3.11/3.12 tested)
* **Google Chrome** (Manifest V3 extensions)

---

## Setup

### 1) Clone

```bash
git clone <your-repo-url>
cd <repo-folder>
```

### 2) Install backend

```bash
pip install -r requirements.txt
```

> This installs Flask, Trafilatura, Readability‑lxml, Newspaper3k, NLTK, pandas, etc.

### 3) NLTK data

The app auto‑downloads `punkt` if missing. Optional one‑time manual download:

```bash
python download_nltk_data.py
```

---

## Run the Flask server

```bash
python app.py
```

* Server endpoint: `http://127.0.0.1:5000/extract`
* Keep this running while you use the extension

---

## Load the Chrome Extension

1. Open `chrome://extensions`
2. Enable **Developer mode**
3. **Load unpacked** → select this repo folder
4. (If prompted) allow downloads and access to `http://127.0.0.1:5000`

---

## Using the Extension

1. Open any news article
2. Click the extension icon
3. Choose **Export format**: JSON / CSV / Excel
4. (Optional) Toggle **ASCII Clean** (straight quotes/dashes)
5. Click **Extract & Download**

**Outputs**

* **JSON**: `{ title, sentences[] }`
* **CSV/Excel**: DataFrame with columns: `line_no`, `sentence`

  * CSV is emitted with **UTF‑8 BOM** so Excel shows quotes/dashes correctly

---

## How it works (under the hood)

1. **Fetch HTML** with a desktop user‑agent
2. **Clean the DOM** (lxml): remove popups/overlays, cookie banners, sidebars/nav/footer, "Editors’ Picks", `figure/figcaption/picture`, iframes, etc.; prefer the main `<article>` node when present
3. **Extract text** via a **3‑stage pipeline**:

   * **Trafilatura** (high recall on news sites)
   * **Readability‑lxml** (main content boil‑down)
   * **Newspaper3k** fallback (cleaned HTML first, then raw)
4. **Sentence splitting** (NLTK `punkt`) with extra normalization to keep titles (Mr./Dr./…)
5. **Export** to JSON / CSV / Excel; optional ASCII normalization

---

## API (for scripts / Postman)

`POST /extract`

**Body (JSON)**

```json
{
  "url": "https://example.com/article",
  "format": "json | csv | xlsx",
  "ascii_clean": false
}
```

**Responses**

* `format = json`

```json
{
  "title": "Page Title",
  "sentences": ["Sentence 1", "Sentence 2", "…"]
}
```

* `format = csv` → `text/csv` with UTF‑8 BOM (download attachment)
* `format = xlsx` → Excel MIME (download attachment)

**cURL examples**

```bash
# JSON
curl -s -X POST http://127.0.0.1:5000/extract \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com/article","format":"json"}' | jq

# CSV (Excel‑friendly)
curl -s -X POST http://127.0.0.1:5000/extract \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com/article","format":"csv"}' \
  -o article.csv

# Excel + ASCII Clean
curl -s -X POST http://127.0.0.1:5000/extract \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com/article","format":"xlsx","ascii_clean":true}' \
  -o article.xlsx
```

---

## File Structure

```
app.py                 # Flask server (extraction, cleaning, exporting)
requirements.txt       # Python deps
download_nltk_data.py  # Optional: one‑time NLTK downloader

manifest.json          # Chrome Extension (MV3)
background.js          # Sends URL to server, handles downloads
popup.html             # UI (format picker, ASCII Clean)
popup.js               # Popup logic

README.md              # This file
```

---

## Troubleshooting

* **Excel shows weird characters (â€œ)**

  * CSVs now include a **UTF‑8 BOM** → Excel will render quotes/dashes correctly
  * Or export **Excel (.xlsx)**, or enable **ASCII Clean** in the popup
* **Only a few sentences extracted**

  * Pipeline tries Trafilatura → Readability → Newspaper3k; if a site still fails, file an issue with the URL
* **Popups/newsletter text in output**

  * The cleaner strips common overlays; if a site uses unusual markup, share the URL to extend the rules
* **No download / no status**

  * Ensure Flask is running without errors; reload extension; check background console (chrome://extensions → Inspect views)
* **NLTK errors**

  * Re‑run `python download_nltk_data.py` or delete and let `app.py` download `punkt` on startup

---

## Credits

* Article extraction: [Trafilatura](https://github.com/adbar/trafilatura) · [Readability-lxml](https://github.com/buriy/python-readability) · [newspaper3k](https://github.com/codelucas/newspaper)
* Sentence splitting: [NLTK](https://www.nltk.org/) (`punkt`) + custom quote/title fixes
* Chrome Extension: Manifest V3

---

## Contributing

PRs welcome! Ideas:

* Site‑specific selectors for tricky publishers
* Additional export formats (Parquet, Markdown)
* Language detection + tokenizer swap

---

## License

MIT © Avijit Roy

---

Built with ❤️ by [Avijit Roy](https://avijitroy.com).
