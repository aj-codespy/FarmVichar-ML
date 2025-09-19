
import firebase_admin
from firebase_admin import credentials, firestore

# Path to your Firebase service account key
# IMPORTANT: Ensure this path is correct and the file exists.
SERVICE_ACCOUNT_KEY_PATH = "/Users/ayushjha/Documents/Programs/KrishiSakhi/venv/keys.json"

try:
    cred = credentials.Certificate(SERVICE_ACCOUNT_KEY_PATH)
    firebase_admin.initialize_app(cred)
    print("Firebase Admin SDK initialized successfully.")
except Exception as e:
    print(f"Error initializing Firebase Admin SDK: {e}")
    # Exit or handle the error appropriately if Firebase is essential
    # For this script, we'll print the error and continue,
    # but the app will not work without a successful connection.
    cred = None

db = firestore.client()

def get_db():
    """
    Dependency function to get the Firestore client.
    In a real app, you might have more complex session management.
    """
    if not cred:
        raise Exception("Firebase Admin SDK is not initialized. Check your service account key path and file.")
    return db
