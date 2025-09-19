# utils/ml_utils.py
from krishisakhi_api import config
from krishisakhi_api import schemas
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, SecretStr

# --- Initialize LangChain Client with a Structured Output Parser ---
# This binds our Pydantic schema to the LLM, forcing it to return valid JSON.
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", api_key=SecretStr(config.GEMINI_API_KEY))
structured_llm = llm.with_structured_output(schemas.DashboardPredictions)

def get_dashboard_predictions(profile: dict, weather: dict) -> dict:
    """
    Uses a single, powerful LLM call to generate all predictive data for the dashboard.
    """
    print(f"Generating full LLM-based dashboard for: {profile.get('full_name')}")
    
    # This "master prompt" asks the LLM to perform all analytical tasks at once.
    prompt = f"""
    You are an expert agricultural analyst for India. Based on the following farmer profile and real-time weather, generate a complete, structured dashboard report.

    **Farmer Profile:**
    - State: {profile.get('state', 'N/A')}
    - District: {profile.get('district', 'N/A')}
    - Primary Crop: {profile.get('primary_crop', 'N/A')}
    - Soil pH: {profile.get('soil_ph', 'N/A')}
    - Soil Nutrients (N,P,K in kg/ha): {profile.get('soil_N', 'N/A')}, {profile.get('soil_P', 'N/A')}, {profile.get('soil_K', 'N/A')}
    - Farming Experience: {profile.get('farming_experience_years', 'N/A')} years
    - Past Pest Issues: {profile.get('past_pest_disease_issues', 'None mentioned')}
    - Government Schemes Applied For: {profile.get('participation_in_govt_schemes', ['None'])}

    **Real-Time Weather Data:**
    - Temperature: {weather.get('temperature', 'N/A')}°C
    - Condition: {weather.get('weather', 'N/A')}
    - Humidity: {weather.get('humidity', 'N/A')}%

    **Your Tasks:**
    1.  **Crop Recommendation**: Recommend the single best crop for the next planting season.
    2.  **Yield Prediction**: Predict the yield in kg/acre for their current primary crop.
    3.  **Pest Risk**: Predict the pest risk as a percentage from 0 to 100.
    4.  **Quality Grading**: Estimate a "Quality Grading Score" from 0 to 100.
    5.  **Price Range**: Provide an estimated market price range (min and max) per quintal for their primary crop in their district.
    6.  **Scheme Analysis**: List relevant government schemes they are likely eligible for, and also list the ones they've already applied for from their profile.
    """
    
    try:
        report = structured_llm.invoke(prompt)
        if isinstance(report, BaseModel):
            return report.dict()
        elif isinstance(report, dict):
            return report
        else:
            return dict(report)
    except Exception as e:
        print(f"Error during LangChain dashboard generation: {e}")
        # Return a default dictionary that matches the schema in case of an error
        return {
            "recommended_crop": "Rice",
            "yield_prediction_kg_acre": 1500.0,
            "pest_risk_percent": 40,
            "quality_grading_score": 75,
            "price_range_per_quintal": {"crop_name": profile.get("primary_crop", "N/A"), "min_price": 2000, "max_price": 2200},
            "applicable_schemes": ["PM-KISAN"],
            "applied_schemes": profile.get("participation_in_govt_schemes", [])
        }