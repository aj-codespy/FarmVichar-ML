# config.py
import os

# --- API Keys ---
# IMPORTANT: Replace these with your actual keys.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOOGLE_KEY_FILE_PATH = os.path.join(PROJECT_ROOT, "keys.json")
# For better security, set them as environment variables.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- Path to your Google Cloud service account key file ---
# This creates a reliable, absolute path to your key file in the root folder.
GOOGLE_KEY_FILE_PATH = os.path.join(PROJECT_ROOT, "keys.json")

GEMINI_API_KEY = 'AIzaSyBozQi2V59ZCzUI6smDyDHt1j9sSSkcZbE'
OPENWEATHER_API_KEY = "b9137d6319bf16636be1ef01db243576"
DATAGOV_API_KEY = "your_datagov_api_key_here"

# --- External Backend Base URL ---
# Can be overridden via env var EXTERNAL_API_BASE
API_BASE_URL = os.environ.get("API_BASE_URL", "https://farmvichardatabase.onrender.com/")

# --- Model Configuration ---
MODEL_NAME = "gemini-2.0-flash"
EMBEDDING_MODEL = "models/embedding-001"

# --- File Paths ---
VECTOR_DB_PATH = os.path.join("vector_db", "faiss_index.index")
DOCS_PATH = os.path.join("vector_db", "docs.txt")

# --- Application Settings ---
# Dictionary of supported languages. Key: language code, Value: display name.
SUPPORTED_LANGUAGES = {
    "ml": "Malayalam",
    "mr": "Marathi",
    "hi": "Hindi",
    "en": "English"
}

# --- Data.gov.in Resource ID ---
MARKET_PRICES_RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"
