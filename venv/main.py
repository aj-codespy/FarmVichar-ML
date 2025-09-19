# main.py
from fastapi import FastAPI, HTTPException, Path, File, UploadFile, Form
from contextlib import asynccontextmanager
import os
import shutil
import json
import datetime
from typing import Optional, Any, Dict
from pydantic import SecretStr, BaseModel

# Import local modules and utility functions
import schemas
import config
import crud
from utils.chatbot_utils import process_chat_query
from utils.ml_utils import get_dashboard_predictions
from utils.api_utils import fetch_weather
from utils.rag_utils import load_faiss_index
from utils.translation_utils import translate_text

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

def transcribe_audio_with_google(audio_bytes: bytes, language_code: str) -> str:
    """Transcribes audio using the Google Speech-to-Text API."""
    client = app_state.get("speech_client")
    if not client: raise HTTPException(status_code=503, detail="Speech client not initialized.")
    try:
        audio = speech.RecognitionAudio(content=audio_bytes)
        config_speech = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.OGG_OPUS,
            sample_rate_hertz=16000,
            language_code=f"{language_code}-IN",
        )
        response = client.recognize(config=config_speech, audio=audio)
        return response.results[0].alternatives[0].transcript if response.results else ""
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to transcribe audio: {e}")

def generate_structured_log(log_notes: str, profile: dict) -> dict:
    """Uses LangChain to parse unstructured text into a structured log."""
    print(f"Generating structured log from notes: '{log_notes}'")
    prompt = f"""
    You are an agricultural data entry specialist. Analyze the following farmer's notes and convert them into a structured log entry.
    
    Farmer's Profile Context:
    - Primary Crop: {profile.get('primary_crop', 'N/A')}
    - Location: {profile.get('village', 'N/A')}, {profile.get('state', 'N/A')}

    Farmer's Notes:
    "{log_notes}"

    Your task is to populate the structured log format. Infer the log_type, crop_name, date, and any specific details like quantities or product names.
    If the date is not mentioned, use today's date: {datetime.date.today().isoformat()}.
    """
    try:
        report = structured_log_parser.invoke(prompt)
        if isinstance(report, BaseModel):
            return report.dict()
        return report
    except Exception as e:
        print(f"Error during LangChain log generation: {e}")
        raise HTTPException(status_code=500, detail="AI failed to structure log data.")

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
    image_file: Optional[UploadFile] = File(None),
    audio_file: Optional[UploadFile] = File(None)
):
    profile = crud.get_user_profile(user_id)
    if not profile: raise HTTPException(status_code=404, detail="User profile not found.")

    user_query, transcribed_text = text_query, None
    user_language = profile.get("preferred_language", "en")

    if audio_file:
        audio_bytes = await audio_file.read()
        transcribed_text = transcribe_audio_with_google(audio_bytes, language_code=user_language)
        user_query = translate_text(transcribed_text, src=user_language, dest='en')
    
    if not user_query: raise HTTPException(status_code=400, detail="No query provided.")
    image_bytes = await image_file.read() if image_file else None
    weather_data = fetch_weather(profile.get('village',''))
    predictions = get_dashboard_predictions(profile, weather_data)
    
    ai_response_text = process_chat_query(
        query=user_query, profile=profile, predictions=predictions,
        faiss_index=app_state["faiss_index"], docs=app_state["docs"],
        language=user_language, image_bytes=image_bytes
    )
    return schemas.ChatResponse(response_text=ai_response_text, transcribed_text=transcribed_text)

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

@app.post("/logs/voice/{user_id}", response_model=schemas.StructuredLog)
async def create_log_from_voice(user_id: str = Path(..., example="ramesh_123"), audio_file: UploadFile = File(...)):
    """Receives a voice note, transcribes it, creates a structured log, and saves it."""
    profile = crud.get_user_profile(user_id)
    if not profile: raise HTTPException(status_code=404, detail="User profile not found.")

    audio_bytes = await audio_file.read()
    user_language = profile.get("preferred_language", "en")
    transcribed_text = transcribe_audio_with_google(audio_bytes, language_code=user_language)

    if not transcribed_text.strip(): raise HTTPException(status_code=400, detail="Audio was empty.")
    
    # 1. Use LangChain to get a guaranteed structured log from the transcribed text
    structured_log = generate_structured_log(transcribed_text, profile)

    # 2. Save the structured log to the database
    crud.save_log_entry(farm_id=user_id, log_data=structured_log)

    return structured_log

@app.get("/alerts/{user_id}", response_model=schemas.AlertsResponse)
def get_proactive_alerts(user_id: str = Path(..., example="ramesh_123")):
    profile = crud.get_user_profile(user_id)
    if not profile: raise HTTPException(status_code=404, detail="User not found.")
    
    alerts = []
    weather = fetch_weather(profile.get('village',''))
    predictions = get_dashboard_predictions(profile, weather)
    
    if predictions.get("pest_risk_percent", 0) > 60:
        alerts.append(schemas.Alert(
            id="ml_pest_risk_01", severity="High", title="High Pest Risk Predicted!",
            message=f"Our AI predicts a high pest risk ({predictions['pest_risk_percent']}%) for your farm.",
            suggestion="We recommend applying a preventive layer of neem oil solution."
        ))
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

