# app.py
# Flask backend for extracting and sentence-splitting news articles via NLTK
# Requires NLTK 'punkt' data downloaded to NLTK_DATA_DIR

from flask import Flask, request, jsonify
from flask_cors import CORS
from newspaper import Article
import os
import nltk

# --- NLTK Data Path Configuration ---
NLTK_DATA_DIR = r'C:\Users\Avijit.Pi-ThinkPad\nltk_data'
nltk.data.path.clear()  # Remove default paths (sanity)
nltk.data.path.append(NLTK_DATA_DIR)

from nltk.tokenize import sent_tokenize

# --- Request Headers for Robust Article Download ---
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'Accept-Language': 'en-US,en;q=0.9',
}

# --- Flask App Initialization ---
app = Flask(__name__)
CORS(app)

# --- API Endpoint: Article Extraction ---
@app.route('/extract', methods=['POST'])
def extract_article():
    """
    Receives a URL, extracts article content, tokenizes it into sentences,
    and returns the title and a list of sentences as JSON.
    """
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'URL not provided'}), 400

    url = data['url']
    print(f"Received URL for processing: {url}")

    try:
        article = Article(url, headers=HEADERS)
        article.download()
        article.parse()
        
        if not article.text:
            print(f"Warning: Parsing succeeded for '{article.title}', but no main text was extracted.")
            return jsonify({'error': 'Could not extract main article text.'})

        print(f"Successfully parsed article: {article.title}")
        
        # Split the article text into sentences
        sentences = sent_tokenize(article.text)
        
        # Respond with title and sentences
        return jsonify({
            'title': article.title,
            'sentences': sentences
        })

    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({'error': str(e)}), 500

# --- Main Execution ---
if __name__ == '__main__':
    app.run(port=5000, debug=True)
