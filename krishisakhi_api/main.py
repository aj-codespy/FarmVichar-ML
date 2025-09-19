# main.py
from fastapi import FastAPI, HTTPException, Path, File, UploadFile, Form
from contextlib import asynccontextmanager
import os
import shutil
import json
from datetime import datetime, timezone
from typing import Optional, Any, Dict
from pydantic import SecretStr, BaseModel
import requests

# Import local modules and utility functions
from krishisakhi_api import schemas
from krishisakhi_api import config
from krishisakhi_api import crud
from krishisakhi_api.utils.chatbot_utils import process_chat_query
from krishisakhi_api.utils.ml_utils import get_dashboard_predictions
from krishisakhi_api.utils.api_utils import fetch_weather
from krishisakhi_api.utils.rag_utils import load_faiss_index
from krishisakhi_api.utils.translation_utils import translate_text

# Import Google Cloud and LangChain libraries
from google.cloud import speech
from google.oauth2 import service_account
from langchain_google_genai import ChatGoogleGenerativeAI

# --- App State & Lifespan Manager ---
app_state = {}

if not hasattr(config, 'GEMINI_API_KEY') or not config.GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is not set in config.py. Please provide your Gemini API key.")
# Initialize LangChain model for structured logging
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", api_key=SecretStr(config.GEMINI_API_KEY))
structured_log_parser = llm.with_structured_output(schemas.StructuredLog)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Server startup: Loading all AI models and resources...")
    try:
        if not os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'keys.json'
        app_state["speech_client"] = speech.SpeechClient()
        print("✅ Google Speech-to-Text client loaded successfully.")
    except Exception as e:
        print(f"❌ CRITICAL: Could not load Google credentials. Error: {e}")
    
    faiss_index, docs = load_faiss_index(config.VECTOR_DB_PATH, config.DOCS_PATH)
    if faiss_index is None:
        print("❌ CRITICAL: FAISS index not found. RAG chatbot will not work.")
    else:
        app_state["faiss_index"], app_state["docs"] = faiss_index, docs
        print("✅ FAISS index and documents loaded successfully.")
    yield
    app_state.clear()
    print("Server shutdown complete.")

app = FastAPI(lifespan=lifespan, title="FarmVichar Service")


# --- Helper Functions ---

# In your main.py or a utils file
from fastapi import HTTPException
from google.cloud import speech
from pydub import AudioSegment
import io

def transcribe_audio_with_google(audio_bytes: bytes, language_code: str) -> str:
    """
    Transcribes any common audio file format using the Google Speech-to-Text API
    by dynamically detecting its properties.
    """
    client = app_state.get("speech_client")
    if not client:
        raise HTTPException(status_code=503, detail="Speech client not initialized.")
    
    try:
        # --- NEW: Use pydub to inspect the audio ---
        audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes))
        
        # Get the audio properties
        sample_rate = audio_segment.frame_rate
        channels = audio_segment.channels
        
        # Google Speech-to-Text works best with lossless formats like LINEAR16 (WAV)
        # We can convert the audio in-memory to this format for best results.
        # This ensures that no matter the input (MP3, OGG, etc.), the format sent to Google is consistent.
        buffer = io.BytesIO()
        audio_segment.export(buffer, format="wav")
        content = buffer.getvalue()

        print(f"Audio properties detected: Sample Rate={sample_rate}, Channels={channels}")
        
        # --- UPDATED: Use dynamic properties in the config ---
        audio = speech.RecognitionAudio(content=content)
        config_speech = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16, # Use LINEAR16 as we converted to WAV
            sample_rate_hertz=sample_rate,
            language_code=f"{language_code}-IN",
            audio_channel_count=channels
        )

        response = client.recognize(config=config_speech, audio=audio)
        
        if response.results:
            transcript = response.results[0].alternatives[0].transcript
            print(f"Google transcribed text (in {language_code}): {transcript}")
            return transcript
        return ""
            
    except Exception as e:
        print(f"Error during Google Speech-to-Text transcription: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to transcribe audio: {e}")

# main.py (or wherever your helper function is located)

import json
from datetime import timezone



def generate_structured_log(transcribed_text: str, farm_id: str) -> dict:
    return {
        "farmId": farm_id,
        "activityType": "general",  # TODO: replace with LLM classification if needed
        "description": transcribed_text,
        "geoLocation": {"lat": 0, "lng": 0},
        "id": None,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    }



# --- API Endpoints ---

@app.get("/dashboard/{user_id}", response_model=schemas.DashboardData)
def get_dashboard_data(user_id: str = Path(..., example="someUniqueUserId")):
    profile = crud.get_user_profile(user_id)
    if not profile: raise HTTPException(status_code=404, detail="User or their farm not found.")
    weather_data = fetch_weather(profile.get('village', ''))
    llm_predictions = get_dashboard_predictions(profile, weather_data)
    return schemas.DashboardData(user_profile=profile, weather=weather_data, predictions=schemas.DashboardPredictions(**llm_predictions))

@app.get("/weather/{user_id}", response_model=dict)
def get_weather_for_user(user_id: str = Path(..., example="ramesh_123")):
    profile = crud.get_user_profile(user_id)
    if not profile: raise HTTPException(status_code=404, detail="User not found.")
    weather_data = fetch_weather(profile.get('village', ''))
    if "error" in weather_data: raise HTTPException(status_code=500, detail=weather_data["error"])
    return weather_data

@app.post("/chat/{user_id}", response_model=schemas.ChatResponse)
async def chat_with_assistant(
    user_id: str = Path(..., example="ramesh_123"),
    text_query: Optional[str] = Form(None),
    language_code: str = Form("en"), # <-- NEW: Language code parameter
    image_file: Optional[UploadFile] = File(None),
    audio_file: Optional[UploadFile] = File(None)
):
    """
    Main conversational endpoint. Handles text, image, and voice.
    Translates the final response into the specified language_code.
    """
    profile = crud.get_user_profile(user_id)
    if not profile: raise HTTPException(status_code=404, detail="User profile not found.")

    user_query, transcribed_text = text_query, None

    # Determine the source language from the user's profile for transcription
    source_language = profile.get("preferredLanguage", "en")

    if audio_file:
        audio_bytes = await audio_file.read()
        transcribed_text = transcribe_audio_with_google(audio_bytes, language_code=source_language)
        # Always translate the transcribed text to English for the RAG pipeline
        user_query = translate_text(transcribed_text, src=source_language, dest='en')
    
    if not user_query: raise HTTPException(status_code=400, detail="No query provided.")
    
    image_bytes = await image_file.read() if image_file else None
    weather_data = fetch_weather(profile.get('village',''))
    predictions = get_dashboard_predictions(profile, weather_data)
    
    # --- Step 1: Get the core AI response in English ---
    english_response = process_chat_query(
        query=user_query, profile=profile, predictions=predictions,
        faiss_index=app_state["faiss_index"], docs=app_state["docs"],
        language='en', # The core processing is done in English
        image_bytes=image_bytes
    )

    # --- Step 2: Translate the English response to the desired output language ---
    final_response_text = translate_text(english_response, src='en', dest=language_code)
    
    return schemas.ChatResponse(response_text=final_response_text, transcribed_text=transcribed_text)

@app.post("/logs/{farm_id}")
def create_log_entry(farm_id: str, log_request: schemas.LogEntry):
    """Receives structured text notes, saves them via the DB Gateway."""
    log_data_to_save = {
        "farmId": farm_id,
        "activityType": log_request.log_type,
        "description": log_request.notes,
        "details": log_request.details
    }
    result = crud.save_log_entry(farm_id=farm_id, log_data=log_data_to_save)
    if not result:
        raise HTTPException(status_code=500, detail="Failed to save log entry via API.")
    return result

from datetime import datetime, timezone

@app.post("/logs/voice/{farm_id}")
async def create_log_from_voice(
    farm_id: str,
    audio_file: UploadFile = File(...),
    language_code: str = Form("mr")
):
    # Step 1. Read audio file
    audio_bytes = await audio_file.read()
    if not audio_bytes:
        return {"status": "skipped", "reason": "Empty audio file"}

    # Step 2. Transcribe
    transcribed_text = transcribe_audio_with_google(audio_bytes, language_code=language_code)
    if not transcribed_text:
        return {"status": "skipped", "reason": "No transcription result"}

    # Step 3. Generate API log
    try:
        api_log = generate_structured_log(transcribed_text, farm_id)
    except Exception as e:
        print(f"Log generation failed: {e}")
        return {"status": "skipped", "reason": "Log generation failed"}

    # Step 4. Ensure timestamp is UTC ISO8601 with Z
    api_log["timestamp"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # Step 5. Save the log entry to the DB
    saved_log_response = crud.save_log_entry(farm_id=farm_id, log_data=api_log)
    if not saved_log_response:
        raise HTTPException(status_code=500, detail="Failed to save log entry to the database.")

    # Step 6. Build structured response
    date_str = datetime.fromisoformat(
        api_log["timestamp"].replace("Z", "+00:00")
    ).astimezone(timezone.utc).strftime("%Y-%m-%d")

    return schemas.VoiceLogResponse(
        transcribed_text=transcribed_text,
        structured_log=schemas.LogEntry(
            notes=api_log.get("description", ""),
            log_type=api_log.get("activityType", ""),
            summary=api_log.get("description", ""),  # summary = description for now
            details=api_log.get("details", {}),
            date=date_str
        )
    )




@app.get("/alerts/{user_id}", response_model=schemas.AlertsResponse)
def get_proactive_alerts(user_id: str = Path(..., example="ramesh_123")):
    raw_alerts = requests.get(f"{config.API_BASE_URL}/api/users/{user_id}/alerts/").json()
    # Only include alerts that have all required fields for schemas.Alert
    alerts = []
    for a in raw_alerts:
        try:
            alerts.append(schemas.Alert(**a))
        except Exception as e:
            print(f"Skipping invalid alert: {a} (reason: {e})")
    return schemas.AlertsResponse(alerts=alerts)

@app.post("/onboarding/voice", response_model=schemas.OnboardingVoiceResponse)
async def fill_form_field_with_voice(audio_file: UploadFile = File(...), question: str = Form(...), field_name: str = Form(...)):
    audio_bytes = await audio_file.read()
    transcribed_text = transcribe_audio_with_google(audio_bytes, language_code="en")
    if not transcribed_text.strip(): raise HTTPException(status_code=400, detail="Audio was empty.")
    
    extracted_value = transcribed_text # Simplified for now, an LLM could refine this
    return schemas.OnboardingVoiceResponse(transcribed_text=transcribed_text, extracted_value=extracted_value)

@app.post("/voice/transcribe", response_model=Dict[str, str])
async def transcribe_voice_utility(audio_file: UploadFile = File(...), language_code: str = Form(..., example="mr")):
    """A general utility to transcribe an audio file into the specified language."""
    audio_bytes = await audio_file.read()
    transcribed_text = transcribe_audio_with_google(audio_bytes, language_code=language_code)
    return {"transcribed_text": transcribed_text}

def save_log_to_api(farm_id: str, structured_log: dict):
    """Saves the structured log to the API. Returns the API response or a default dict if failed."""
    if not farm_id or not structured_log:
        print("Missing farm_id or structured_log, skipping save.")
        return {"status": "skipped", "reason": "Missing farm_id or structured_log"}
    try:
        result = crud.save_log_entry(farm_id, structured_log)
        if not result:
            print("Failed to save log entry via API.")
            return {"status": "failed", "reason": "API error"}
        return result
    except Exception as e:
        print(f"Exception in save_log_to_api: {e}")
        return {"status": "error", "reason": str(e)}

