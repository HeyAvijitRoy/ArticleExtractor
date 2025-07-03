# Article Extractor (Newspaper3k + Chrome Extension)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Extract clean sentences from news articles with one click, right from your browser.

---

## Project Overview

This tool is a Chrome Extension that connects to a local Flask server using [newspaper3k](https://github.com/codelucas/newspaper) and [NLTK](https://www.nltk.org/) to extract the content of news articles and export it as a JSON file of sentences.

* **One-click extraction:** Download sentences from any news/web article instantly.
* **NLP-grade results:** Robust parsing and sentence tokenization using NLTK `punkt`.
* **Local & private:** All processing is local; no article data leaves your machine.
* **Simple UI:** Clean status updates and download flow.

---

## Initial Setup

### 1. Clone the Repository

```
git clone <your-repo-url>
cd <repo-folder>
```

### 2. Install Python Dependencies (Backend)

> **Python 3.8+ recommended**

```
pip install flask flask-cors newspaper3k nltk==3.8.1
```

### 3. Download NLTK 'punkt' Model

> Run this **once** to get NLTK's sentence splitter:

```
python download_nltk_data.py
```

* This downloads the tokenizer to your user `nltk_data` folder (cross-platform, no hardcoding).

---

## Running the Flask Server

```
python app.py
```

* The server listens at: `http://127.0.0.1:5000/extract`
* Leave this terminal running while using the extension.

---

## Chrome Extension: Setup & Usage

### 1. Load the Extension (Developer Mode)

* Go to `chrome://extensions` in Chrome
* Enable **Developer Mode** (top right)
* Click **Load unpacked** and select the repo folder

### 2. Permissions

* Approve downloads and localhost access if prompted.

### 3. Usage

1. Open any article in Chrome
2. Click the extension icon, then click **Extract Text & Download JSON**
3. A `.json` file will be downloaded containing the article’s sentences

---

## File Structure

* `app.py` – Flask server (Python)
* `download_nltk_data.py` – NLTK model downloader (Python)
* `background.js` – Extension background logic (JS)
* `popup.js` – Extension popup logic (JS)
* `popup.html` – UI for the extension popup
* `manifest.json` – Chrome extension config (MV3)

---

## Troubleshooting

* **No download/status?**

  * Ensure Flask server is running, with no errors
  * Reload the extension in `chrome://extensions` after edits
  * Approve permissions for downloads and localhost requests
  * Some browsers may block `http://127.0.0.1`; see Chrome flags or try Edge/Firefox
  * If you see NLTK errors, re-run `download_nltk_data.py` or check `nltk_data` path in `app.py`
* **Still stuck?**

  * Check the extension background page console for errors
  * Test Flask directly with curl/Postman

---

## Credits

* Article extraction: [newspaper3k](https://github.com/codelucas/newspaper)
* Sentence splitting: [NLTK](https://www.nltk.org/) | [nltk.PyPI 3.8.1](https://pypi.org/project/nltk/3.8.1/#files)
* Chrome Extension: Manifest V3
* Author: [Avijit Roy](https://www.linkedin.com/in/HeyAvijitRoy/)

---

Built with ❤️ by [Avijit Roy](https://avijitroy.com).
