# utils/api_utils.py
import requests
from krishisakhi_api.config import OPENWEATHER_API_KEY, DATAGOV_API_KEY, MARKET_PRICES_RESOURCE_ID

def fetch_weather(village: str) -> dict:
    """Fetches weather data with comprehensive error handling."""
    url = f"https://api.openweathermap.org/data/2.5/weather?q={village},IN&appid={OPENWEATHER_API_KEY}&units=metric"
    print(f"[API] Fetching weather data from: {url}")
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        data = response.json()
        print("[API] Successfully fetched weather data.")
        return {
            "temperature": data['main']['temp'],
            "weather": data['weather'][0]['description'].title(),
            "rain": data.get('rain', {}).get('1h', 0)
        }
    except requests.exceptions.HTTPError as e:
        print(f"❌ ERROR [API]: HTTP Error fetching weather. Status Code: {e.response.status_code}, Response: {e.response.text}")
        return {"error": f"Weather data not found for '{village}'. Check spelling."}
    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR [API]: Network error fetching weather. Reason: {e}")
        return {"error": "Could not connect to weather service."}
    except KeyError as e:
        print(f"❌ ERROR [API]: Unexpected weather data format. Missing key: {e}")
        return {"error": "Received incomplete weather data."}


def fetch_gov_info(crop: str) -> dict:
    """
    Fetches government data.
    THIS FUNCTION IS CURRENTLY DISABLED.
    """
    # --- NEW CODE ---
    # This function now immediately returns an error message without calling the API.
    print("[API] Government data fetch is currently disabled.")
    return {"error": "Gov & Market Info is disabled."}

    # --- ORIGINAL CODE (Commented Out for easy restoration) ---
    # url = f"https://api.data.gov.in/resource/{MARKET_PRICES_RESOURCE_ID}?api-key={DATAGOV_API_KEY}&format=json&limit=5&filters[commodity]={crop.capitalize()}"
    # print(f"[API] Fetching government data from: {url}")
    # try:
    #     response = requests.get(url, timeout=15)
    #     response.raise_for_status()
    #     data = response.json()
    #
    #     records = data.get('records', [])
    #     if records:
    #         print("[API] Successfully fetched and parsed government data.")
    #         latest = records[0]
    #         return {
    #             "market_price": latest.get('modal_price', 'N/A'),
    #             "market_location": latest.get('market', 'N/A'),
    #             "scheme_info": "PM-KISAN: Eligible farmers receive Rs. 6000 per year."
    #         }
    #     else:
    #         print(f"[API] No market records found for crop: {crop}")
    #         return {"error": f"No market data found for {crop}."}
    #
    # except requests.exceptions.RequestException as e:
    #     print(f"❌ ERROR [API]: Network error fetching gov data. Reason: {e}")
    #     return {"error": "Could not connect to government data service."}
    # except Exception as e:
    #     print(f"❌ ERROR [API]: Unexpected error parsing gov data. Reason: {e}")
    #     return {"error": "Could not process government data."}