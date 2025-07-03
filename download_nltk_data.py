import nltk
import os

NLTK_DATA_DIR = r'C:\Users\Avijit.Pi-ThinkPad\nltk_data'

print("--- NLTK Data Downloader ---")
print("This script will download the 'punkt' tokenizer models to:")
print(f"  {NLTK_DATA_DIR}")
print("This is a one-time setup.\n")

# Ensure the directory exists
os.makedirs(NLTK_DATA_DIR, exist_ok=True)

try:
    # Explicitly download to your data dir, force refresh
    nltk.download('punkt', download_dir=NLTK_DATA_DIR, force=True)
    print("\nSuccessfully downloaded 'punkt' models.")
    print("You can now run the main 'app.py' server.")
except Exception as e:
    print(f"\nAn error occurred during download: {e}")
    print("Please check your internet connection and try again.")
