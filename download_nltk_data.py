import nltk
import os

# Use the user's home directory for nltk_data
NLTK_DATA_DIR = os.path.join(os.path.expanduser("~"), "nltk_data")

print("--- NLTK Data Downloader ---")
print("This script will download the 'punkt' tokenizer models to:")
print(f"  {NLTK_DATA_DIR}")
print("This is a one-time setup.\n")

os.makedirs(NLTK_DATA_DIR, exist_ok=True)

try:
    nltk.download('punkt', download_dir=NLTK_DATA_DIR, force=True)
    print("\nSuccessfully downloaded 'punkt' models.")
    print("You can now run the main 'app.py' server.")
except Exception as e:
    print(f"\nAn error occurred during download: {e}")
    print("Please check your internet connection and try again.")
