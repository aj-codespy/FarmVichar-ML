# crud.py
import requests
from krishisakhi_api import config
from typing import Optional, Dict, List, Any

# --- Helper function to handle API requests ---
def _make_api_request(method: str, endpoint: str, json_data: Optional[Dict] = None) -> Optional[Any]:
    """A centralized function to make API calls and handle errors."""
    url = f"{config.API_BASE_URL}{endpoint}"
    print(f"Making {method} request to: {url}")
    try:
        if method.upper() == 'GET':
            response = requests.get(url, timeout=15)
        elif method.upper() == 'POST':
            response = requests.post(url, json=json_data, timeout=15)
        else:
            raise ValueError("Unsupported HTTP method")
            
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ API request failed for {url}: {e}")
        return None

# --- User and Farm Profile Functions ---
def get_user_profile(user_id: str) -> Optional[Dict]:
    """
    Retrieves a user's primary farm profile.
    This function simulates fetching the main farm associated with a user.
    For simplicity, we'll assume user_id can be used to find the primary farm_id.
    In a real app, you might first get the user, then their list of farms.
    """
    # Based on your schema, we first need to get the user's farms.
    # We will assume the first farm returned is the primary one for this service.
    farms = _make_api_request('GET', f'/api/users/{user_id}/farms/')
    if farms and isinstance(farms, list) and len(farms) > 0:
        primary_farm = farms[0]
        # To get a complete profile, you might need to fetch data from other collections too.
        # This function will return the core farm document.
        print(f"✅ Fetched primary farm profile for user: {user_id}")
        return primary_farm
    print(f"⚠️ No farms found for user: {user_id}")
    return None

# --- Logging Functions ---
def save_log_entry(farm_id: str, log_data: dict) -> Optional[Dict]:
    """
    Saves a structured log entry (activity) for a specific farm.
    """
    # The log_data should match the schema for the 'logs' collection
    # Example: {"activityType": "Irrigation", "description": "Drip for 2 hours"}
    return _make_api_request('POST', f'/api/farms/{farm_id}/activities', json_data=log_data)


# --- Functions that your ML service might need but don't have a direct CRUD endpoint ---
# These are placeholder functions because the logic is handled by other services (e.g., chat backend).

def save_chat_turn(user_id: str, query: str, response: str, **kwargs) -> Dict:
    """
    Placeholder: The main backend would handle saving chat messages.
    This ML service does not directly write to the chats collection.
    """
    print(f"✅ [INFO] Chat turn for {user_id} would be saved by the main backend.")
    return {"status": "not_applicable_for_this_service"}

def update_user_summary(user_id: str, summary_data: dict) -> Dict:
    """
    Placeholder: The main backend would handle updating derived data like summaries or scores.
    The ML service's role is to provide the data for the update.
    """
    print(f"✅ [INFO] User summary update for {user_id} would be handled by the main backend.")
    return {"status": "not_applicable_for_this_service"}