# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
from newspaper import Article, Config

# Configuration for newspaper3k
# Set a user agent to avoid issues with some websites that block requests without a user agent
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
config = Config()
config.browser_user_agent = USER_AGENT
config.request_timeout = 10 # Set a 10-second timeout for requests

app = Flask(__name__)
# CORS is required to allow the Chrome extension to make requests to this server
CORS(app)
@app.route('/extract', methods=['POST'])
def extract_article():
    """
    Receives a URL from a POST request, extracts the article content using newspaper3k,
    and returns the title and text as JSON.
    """
    # Get the JSON data from the request
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'URL not provided'}), 400

    url = data['url']
    print(f"Received URL for processing: {url}")

    try:
        # Create an Article object
        article = Article(url, config=config)
        
        # Download and parse the article
        article.download()
        article.parse()
        
        print(f"Successfully parsed article: {article.title}")
        
        # Return the extracted data
        return jsonify({
            'title': article.title,
            'text': article.text
        })

    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({'error': str(e)}), 500

# --- Main Execution ---
if __name__ == '__main__':
    # Runs the Flask app on localhost at port 5000
    app.run(port=5000, debug=True)

