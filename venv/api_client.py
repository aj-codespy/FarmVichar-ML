# api_client.py
import requests
import config
from typing import Optional, Dict, Any

def _make_api_request(method: str, endpoint: str, json_data: Optional[Dict] = None) -> Optional[Any]:
    """A centralized function to make API calls to the database gateway."""
    url = f"{config.DB_API_BASE_URL}{endpoint}"
    print(f"Calling DB Gateway: {method} {url}")
    try:
        if method.upper() == 'GET':
            response = requests.get(url, timeout=15)
        elif method.upper() == 'POST':
            response = requests.post(url, json=json_data, timeout=15)
        else:
            raise ValueError("Unsupported HTTP method")
            
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ DB Gateway request failed for {url}: {e}")
        return None

# --- User & Farm Functions ---
def get_user_profile(user_id: str) -> Optional[Dict]:
    """
    Retrieves the main profile for a user by fetching their first farm's details.
    """
    # 1. Get all farms for the user
    farms = _make_api_request('GET', f'/api/users/{user_id}/farms/')
    if not farms:
        return None
    
    # 2. Assume the first farm is the primary one and get its full details
    primary_farm_id = farms[0].get('id')
    if not primary_farm_id:
        return None
        
    farm_details = _make_api_request('GET', f'/api/farms/{primary_farm_id}')
    
    # In a real app, you would merge data from /crops, /resources etc.
    # For now, the farm detail is our main "profile".
    return farm_details

# --- Logging Functions ---
def save_log_entry(farm_id: str, log_data: dict) -> Optional[Dict]:
    """Saves an activity log for a specific farm."""
    # The log_data should match your LogCreate schema
    # Example: {"activityType": "Irrigation", "description": "Watered for 2 hours."}
    return _make_api_request('POST', f'/api/farms/{farm_id}/logs/', json_data=log_data)

# --- Alert Functions ---
def create_alert(user_id: str, alert_data: dict) -> Optional[Dict]:
    """Creates a new alert for a specific user."""
    # The alert_data should match your AlertCreate schema
    # Example: {"alertType": "Pest", "message": "High risk detected...", "priority": 3}
    return _make_api_request('POST', f'/api/users/{user_id}/alerts/', json_data=alert_data)