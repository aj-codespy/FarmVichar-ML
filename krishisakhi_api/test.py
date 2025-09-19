import os
import datetime
from typing import Optional, Dict
from pydantic import BaseModel, Field, SecretStr
from langchain_google_genai import ChatGoogleGenerativeAI

# --- 1. Setup: Recreate necessary components for the test ---

# Mock the config module for this standalone script
class MockConfig:
    # IMPORTANT: Replace this with your actual Gemini API Key
    GEMINI_API_KEY = "AIzaSyBozQi2V59ZCzUI6smDyDHt1j9sSSkcZbE" 

config = MockConfig()

# Define the Pydantic schema the function depends on
from typing import Union

class StructuredLog(BaseModel):
    log_type: str
    date: str
    crop_name: Optional[str]
    summary: str
    details: Union[Dict[str, str], str] = Field(default_factory=dict)

# Initialize the LangChain structured output model
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", api_key=SecretStr(config.GEMINI_API_KEY))
structured_log_parser = llm.with_structured_output(StructuredLog)


# --- 2. The Function to Test ---
# (Copied directly from your project)

import json

def generate_structured_log(log_notes: str, profile: dict) -> dict:
    print(f"Generating structured log from notes: '{log_notes}'")
    today_date = datetime.date.today().isoformat()
    
    prompt = f"""
    You are an expert agricultural data entry specialist. Analyze the following farmer's notes and convert them into a structured JSON object that strictly follows the 'StructuredLog' schema.

    **Farmer's Profile Context:**
    - Primary Crop: {profile.get('primary_crop', 'N/A')}

    **Farmer's Notes:**
    "{log_notes}"

    **Your Task:**
    Populate a JSON object with the following keys. The `log_type`, `date`, and `summary` fields are mandatory.

    - `log_type`: Infer the type of activity.
    - `date`: Infer from the text. If no date is mentioned, use today's date: {today_date}.
    - `crop_name`: Infer from the text or the user's primary crop.
    - `summary`: Provide a concise one-sentence summary of the activity.
    - `details`: MUST be a **raw JSON object**, not a string. Example:
      ✅ `"details": {{"fertilizer": "Urea", "quantity": "50 kg"}}`
      ❌ `"details": "{{'fertilizer': 'Urea', 'quantity': '50 kg'}}"`
    
    Return **only the raw JSON object** and nothing else.
    """

    try:
        report = structured_log_parser.invoke(prompt)

        # Convert to dict
        result = report.model_dump()

        # If details comes back as string, try to parse
        if isinstance(result["details"], str):
            result["details"] = json.loads(result["details"])

        print(result)
        return result
    except Exception as e:
        print(f"\n❌ Error during LangChain log generation: {e}")
        return {}

generate_structured_log("Applied 50kg of Urea to the paddy crop today.", {"primary_crop": "Paddy"})