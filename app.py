# app.py
# Flask backend for extracting and sentence-splitting news articles via NLTK
# Stronger pipeline + cleaning + smarter sentence splitting around quotes/titles.

from flask import Flask, request, jsonify
from flask_cors import CORS
from newspaper import Article
import os
import nltk
import requests
import json
import re
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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                  " (KHTML, like Gecko) Chrome/115.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# ---------- Cleaning helpers ----------
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

    # 1) Obvious overlays/popups by class/id keywords
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

    # 2) Dialog roles
    _remove_matches(doc, "//*[@role='dialog' or @role='alertdialog']")

    # 3) Inline styles that scream overlay
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

    # 4) Scripts/iframes and common non-content regions
    _remove_matches(doc, '//script | //noscript | //iframe')
    _remove_matches(doc, '//nav | //footer | //aside | //*[@role="complementary"] | //*[@role="navigation"] | //*[@role="contentinfo"]')

    # 5) Remove editorial side modules
    side_block_keywords = [
        "editors’ picks","editor’s picks","editors' picks","most popular","trending",
        "you might have missed","sponsored","from around the web","recommended","more stories"
    ]
    _remove_if_text_found(doc, '//h1|//h2|//h3|//h4|//div|//section', side_block_keywords, bubble_up_levels=2)

    # 6) Remove image containers/captions to avoid caption text
    _remove_matches(doc, '//figure | //figcaption | //picture')

    # 7) Prefer keeping only the <article> contents, if available
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

    # 8) schema.org Article fallback
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

    # Otherwise return cleaned full doc
    try:
        return lxml_html.tostring(doc, encoding='unicode')
    except Exception:
        return raw_html

# ---------- Sentence cleanup helpers ----------
TITLE_TOKENS = {"Mr.", "Ms.", "Mrs.", "Dr.", "Prof.", "Sr.", "Jr.", "Gen.", "Sen.", "Rep.", "Gov.", "St."}
TITLE_RE = r'(Mr|Ms|Mrs|Dr|Prof|Sen|Rep|Gov|Gen|St|Sr|Jr)\.'

def normalize_for_tokenization(text: str) -> str:
    """
    Fix common joins that confuse sentence tokenizers:
    - 'Italy.Mr.' -> 'Italy. Mr.'
    - 'Very friendly.”Mr.' -> 'Very friendly.” Mr.'
    """
    # Space after a period when next char is Capital and char before dot is lowercase
    text = re.sub(r'(?<=[a-z])\.(?=[A-Z])', '. ', text)

    # Space before courtesy titles when glued to a period: 'Italy.Mr.' -> 'Italy. Mr.'
    text = re.sub(r'\.(?=\s*' + TITLE_RE + r')', '. ', text)

    # Space after a closing quote if a title follows (handles ” and ")
    text = re.sub(r'([\.!?][»”"])\s*(?=' + TITLE_RE + r')', r'\1 ', text)
    # Also if there was no punctuation before the quote: '”Mr.' -> '” Mr.'
    text = re.sub(r'([»”"])(?=' + TITLE_RE + r')', r'\1 ', text)

    # Collapse excessive internal whitespace
    text = re.sub(r'[ \t]+', ' ', text)
    return text

def stitch_sentence_fragments(sents):
    """
    1) Merge tiny fragments like 'Mr.' / 'Ms.' / 'Dr.' that got split off.
    2) If a sentence ends with a title token (rare), merge it with the next one.
    """
    merged = []
    i = 0
    while i < len(sents):
        cur = sents[i].strip()

        # Case A: standalone courtesy title or single-letter initial
        if cur in TITLE_TOKENS or re.fullmatch(r'[A-Z]\.', cur):
            if i + 1 < len(sents):
                nxt = sents[i + 1].lstrip()
                if merged:
                    merged[-1] = merged[-1].rstrip() + ' ' + cur + ' ' + nxt
                else:
                    merged.append(cur + ' ' + nxt)
                i += 2
                continue

        # Case B: sentence ends with a title token (e.g., '... ” Mr.' as end)
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

# ---------- Extractors ----------
def extract_with_trafilatura(cleaned_html: str, url: str):
    try:
        result = trafilatura.extract(
            cleaned_html,
            url=url,
            output="json",
            with_metadata=True,
            include_images=False,
            include_tables=False,
            favor_recall=True,
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

# ---------- Flask app ----------
app = Flask(__name__)
CORS(app)

@app.route('/extract', methods=['POST'])
def extract_article():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'URL not provided'}), 400

    url = data['url']
    print(f"Received URL for processing: {url}")

    try:
        # 1) Fetch raw HTML
        resp = requests.get(url, headers=HEADERS, timeout=25)
        resp.raise_for_status()
        raw_html = resp.text

        # 2) Clean overlays/junk
        cleaned_html = remove_overlays_sidebars_and_junk(raw_html)

        # 3) Try extractors in order
        title, text = extract_with_trafilatura(cleaned_html, url)
        if not text:
            title, text = extract_with_readability(cleaned_html)
        if not text:
            title, text = extract_with_newspaper(url, cleaned_html)
        if not text:
            title, text = extract_with_newspaper(url)

        if not text:
            return jsonify({'error': 'Could not extract main article text.'}), 200

        # 4) Normalize, tokenize, stitch
        text = normalize_for_tokenization(text)
        sentences = sent_tokenize(text)
        sentences = stitch_sentence_fragments(sentences)

        # 5) Title fallback
        if not title:
            try:
                doc = Document(raw_html)
                title = (doc.short_title() or doc.title() or "").strip()
            except Exception:
                title = ""

        return jsonify({
            'title': title,
            'sentences': sentences
        })

    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000, debug=True)
