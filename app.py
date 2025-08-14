# app.py
# Strong extractor pipeline + cleaning + smarter sentence splitting
# Now: DataFrame export (CSV/XLSX), CSV uses UTF-8 BOM for Excel, optional ASCII normalization.

from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from newspaper import Article
import os
import nltk
import requests
import json
import re
from io import BytesIO
import pandas as pd
from lxml import html as lxml_html
from lxml import etree as lxml_etree
from readability import Document
import trafilatura

# ---------- NLTK setup ----------
NLTK_DATA_DIR = os.path.join(os.path.expanduser("~"), "nltk_data")
os.makedirs(NLTK_DATA_DIR, exist_ok=True)
try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt", download_dir=NLTK_DATA_DIR)
nltk.data.path.clear()
nltk.data.path.append(NLTK_DATA_DIR)
from nltk.tokenize import sent_tokenize

# ---------- Request headers ----------
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# ---------- Flask app ----------
app = Flask(__name__)
CORS(app, expose_headers=["X-File-Name"])  # let extension read custom header

# ---------- HTML cleaning helpers ----------
def _remove_matches(doc, xpath_expr):
    for el in doc.xpath(xpath_expr):
        parent = el.getparent()
        if parent is not None:
            parent.remove(el)

def _remove_if_text_found(doc, xpath_expr, keywords, bubble_up_levels=1):
    for node in doc.xpath(xpath_expr):
        text = (node.text_content() or "").strip().lower()
        if any(kw in text for kw in keywords):
            victim = node
            for _ in range(bubble_up_levels):
                if victim.getparent() is not None:
                    victim = victim.getparent()
            par = victim.getparent()
            if par is not None:
                par.remove(victim)

def remove_overlays_sidebars_and_junk(raw_html: str) -> str:
    try:
        doc = lxml_html.fromstring(raw_html)
    except Exception:
        return raw_html

    block_keywords = [
        "modal","popup","overlay","banner","cookie","gdpr",
        "subscribe","newsletter","consent","paywall","signin",
        "signup","login","tooltip","toast","lightbox","offcanvas",
        "advert","advertisement","sponsored","adunit","ad-container",
        "interstitial","promo"
    ]
    for kw in block_keywords:
        _remove_matches(doc, f"//*[contains(translate(@class,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{kw}')]")
        _remove_matches(doc, f"//*[contains(translate(@id,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{kw}')]")

    _remove_matches(doc, "//*[@role='dialog' or @role='alertdialog']")

    for el in list(doc.xpath('//*[@style]')):
        style = (el.attrib.get('style') or '').lower().replace(' ', '')
        kill = False
        if 'position:fixed' in style or 'position:sticky' in style:
            kill = True
        if 'z-index' in style and any(x in style for x in ['9999','2147483647','999','1000']):
            kill = True
        if kill:
            par = el.getparent()
            if par is not None:
                par.remove(el)

    _remove_matches(doc, '//script | //noscript | //iframe')
    _remove_matches(doc, '//nav | //footer | //aside | //*[@role="complementary"] | //*[@role="navigation"] | //*[@role="contentinfo"]')

    side_block_keywords = [
        "editors’ picks","editor’s picks","editors' picks","most popular","trending",
        "you might have missed","sponsored","from around the web","recommended","more stories"
    ]
    _remove_if_text_found(doc, '//h1|//h2|//h3|//h4|//div|//section', side_block_keywords, bubble_up_levels=2)

    _remove_matches(doc, '//figure | //figcaption | //picture')

    articles = doc.xpath('//article')
    if articles:
        article_el = articles[0]
        new_root = lxml_etree.Element('html')
        body = lxml_etree.SubElement(new_root, 'body')
        body.append(lxml_html.fromstring(lxml_html.tostring(article_el)))
        try:
            return lxml_html.tostring(new_root, encoding='unicode')
        except Exception:
            pass

    schema_nodes = doc.xpath('//*[@itemtype="http://schema.org/Article" or @itemtype="https://schema.org/Article"]')
    if schema_nodes:
        candidate = schema_nodes[0]
        new_root = lxml_etree.Element('html')
        body = lxml_etree.SubElement(new_root, 'body')
        body.append(lxml_html.fromstring(lxml_html.tostring(candidate)))
        try:
            return lxml_html.tostring(new_root, encoding='unicode')
        except Exception:
            pass

    try:
        return lxml_html.tostring(doc, encoding='unicode')
    except Exception:
        return raw_html

# ---------- Sentence cleanup ----------
TITLE_TOKENS = {"Mr.", "Ms.", "Mrs.", "Dr.", "Prof.", "Sr.", "Jr.", "Gen.", "Sen.", "Rep.", "Gov.", "St."}
TITLE_RE = r'(Mr|Ms|Mrs|Dr|Prof|Sen|Rep|Gov|Gen|St|Sr|Jr)\.'

def normalize_for_tokenization(text: str) -> str:
    text = re.sub(r'(?<=[a-z])\.(?=[A-Z])', '. ', text)                   # Italy.Mr. -> Italy. Mr.
    text = re.sub(r'\.(?=\s*' + TITLE_RE + r')', '. ', text)              # ensure space before title
    text = re.sub(r'([\.!?][»”"])\s*(?=' + TITLE_RE + r')', r'\1 ', text) # …”Mr. -> …” Mr.
    text = re.sub(r'([»”"])(?=' + TITLE_RE + r')', r'\1 ', text)          # ”Mr. -> ” Mr.
    text = re.sub(r'[ \t]+', ' ', text)
    return text

def stitch_sentence_fragments(sents):
    merged = []
    i = 0
    while i < len(sents):
        cur = sents[i].strip()
        if cur in TITLE_TOKENS or re.fullmatch(r'[A-Z]\.', cur):
            if i + 1 < len(sents):
                nxt = sents[i + 1].lstrip()
                if merged:
                    merged[-1] = merged[-1].rstrip() + ' ' + cur + ' ' + nxt
                else:
                    merged.append(cur + ' ' + nxt)
                i += 2
                continue
        if re.search(r'(?:\b' + TITLE_RE + r')\s*$', cur):
            if i + 1 < len(sents):
                nxt = sents[i + 1].lstrip()
                cur = cur.rstrip() + ' ' + nxt
                merged.append(cur)
                i += 2
                continue
        merged.append(cur)
        i += 1
    return merged

# --- Optional ASCII normalization (smart quotes/dashes -> plain) ---
ASCII_MAP = {
    '\u2018': "'", '\u2019': "'", '\u201A': ',', '\u201B': "'",
    '\u201C': '"', '\u201D': '"', '\u201E': '"', '\u00AB': '"', '\u00BB': '"',
    '\u2013': '-', '\u2014': '-', '\u2015': '-', '\u2212': '-',
    '\u2026': '...', '\u00A0': ' ', '\u2009': ' ', '\u200A': ' ',
    '\u200B': '',  '\uFEFF': ''
}
def ascii_clean_text(s: str) -> str:
    return ''.join(ASCII_MAP.get(ch, ch) for ch in s)

# ---------- Extractors ----------
def extract_with_trafilatura(cleaned_html: str, url: str):
    try:
        result = trafilatura.extract(
            cleaned_html, url=url, output="json", with_metadata=True,
            include_images=False, include_tables=False, favor_recall=True
        )
        if not result:
            return None, None
        data = json.loads(result)
        text = (data.get("text") or "").strip()
        title = (data.get("title") or "").strip()
        if text and len(text) > 600:
            return title or None, text
        if text and len(text) > 300:
            return title or None, text
        return None, None
    except Exception:
        return None, None

def extract_with_readability(cleaned_html: str):
    try:
        doc = Document(cleaned_html)
        title = (doc.short_title() or doc.title() or "").strip()
        summary_html = doc.summary(html_partial=True)
        node = lxml_html.fromstring(summary_html)
        text = (node.text_content() or "").strip()
        text = " ".join(text.split())
        if text and len(text) > 400:
            return title or None, text
        return None, None
    except Exception:
        return None, None

def extract_with_newspaper(url: str, cleaned_html: str = None):
    try:
        if cleaned_html:
            art = Article(url, headers=HEADERS)
            art.set_html(cleaned_html)
            art.parse()
        else:
            art = Article(url, headers=HEADERS)
            art.download()
            art.parse()
        txt = (art.text or "").strip()
        ttl = (art.title or "").strip()
        if txt:
            return ttl or None, txt
        return None, None
    except Exception:
        return None, None

# ---------- helpers ----------
def safe_filename(title: str, ext: str) -> str:
    base = (title or "article").lower()
    base = re.sub(r'[^a-z0-9]+', '_', base).strip('_') or 'article'
    return f"{base}.{ext}"

# ---------- Route ----------
@app.route('/extract', methods=['POST'])
def extract_article():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'URL not provided'}), 400

    url = data['url']
    out_format = (data.get('format') or 'json').lower().strip()
    ascii_clean = bool(data.get('ascii_clean', False))
    print(f"Received URL: {url} | format={out_format} | ascii_clean={ascii_clean}")

    try:
        resp = requests.get(url, headers=HEADERS, timeout=25)
        resp.raise_for_status()
        raw_html = resp.text

        cleaned_html = remove_overlays_sidebars_and_junk(raw_html)

        title, text = extract_with_trafilatura(cleaned_html, url)
        if not text:
            title, text = extract_with_readability(cleaned_html)
        if not text:
            title, text = extract_with_newspaper(url, cleaned_html)
        if not text:
            title, text = extract_with_newspaper(url)

        if not text:
            return jsonify({'error': 'Could not extract main article text.'}), 200

        text = normalize_for_tokenization(text)
        sentences = sent_tokenize(text)
        sentences = stitch_sentence_fragments(sentences)

        if ascii_clean:
            sentences = [ascii_clean_text(s) for s in sentences]
            if title:
                title = ascii_clean_text(title)

        if not title:
            try:
                doc = Document(raw_html)
                title = (doc.short_title() or doc.title() or "").strip()
            except Exception:
                title = ""

        # ----- JSON (default) -----
        if out_format == 'json':
            return jsonify({'title': title, 'sentences': sentences})

        # ----- DataFrame: CSV/XLSX -----
        df = pd.DataFrame({
            'line_no': list(range(1, len(sentences)+1)),
            'sentence': sentences
        })

        if out_format == 'csv':
            csv_text = df.to_csv(index=False)        # str
            csv_bytes = csv_text.encode('utf-8-sig') # add BOM so Excel reads UTF-8
            filename = safe_filename(title, 'csv')
            return Response(
                csv_bytes,
                mimetype='text/csv; charset=utf-8',
                headers={
                    'X-File-Name': filename,
                    'Content-Disposition': f'attachment; filename="{filename}"'
                }
            )

        if out_format == 'xlsx':
            bio = BytesIO()
            with pd.ExcelWriter(bio, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='sentences')
            bio.seek(0)
            filename = safe_filename(title, 'xlsx')
            return Response(
                bio.getvalue(),
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                headers={
                    'X-File-Name': filename,
                    'Content-Disposition': f'attachment; filename="{filename}"'
                }
            )

        # Unknown format -> default JSON
        return jsonify({'title': title, 'sentences': sentences})

    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000, debug=True)
