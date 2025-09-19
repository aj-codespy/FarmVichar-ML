# utils/chatbot_utils.py
from krishisakhi_api import config
from krishisakhi_api.utils.translation_utils import translate_text
from krishisakhi_api.utils.rag_utils import rag_retrieve
import io
from PIL import Image
import google.generativeai as genai

# Configure Gemini API key globally (if needed)
genai.configure(api_key=config.GEMINI_API_KEY)
llm_model = genai.GenerativeModel(config.MODEL_NAME)

def analyze_image_with_gemini(image_bytes: bytes) -> str:
    """Uses Gemini's multimodal capability to analyze the provided image."""
    try:
        image = Image.open(io.BytesIO(image_bytes))
        prompt = "Analyze this image from a farm. Describe crop health, visible pests, diseases, or soil conditions. Be factual, concise, and respond in English."
        response = llm_model.generate_content([prompt, image])
        return response.text.strip()
    except Exception as e:
        print(f"Image analysis failed: {e}")
        return "Could not analyze the uploaded image."

def process_chat_query(query: str, profile: dict, predictions: dict, faiss_index, docs: list[str], language: str, image_bytes: bytes | None = None) -> str:
    """
    Processes a user's chat query using the full RAG and multimodal pipeline.
    """
    # Translate the native language query to English first for RAG and prompts
    eng_query = translate_text(query, src=language, dest='en')
    
    native_language_name = config.SUPPORTED_LANGUAGES.get(language, language)
    
    image_analysis = "No image provided."
    if image_bytes:
        # This call will now work correctly
        image_analysis = analyze_image_with_gemini(image_bytes)
    rag_context = rag_retrieve(eng_query, faiss_index, docs)
    
    prompt = f"""
    You are 'Krishi Sakhi', an AI farming assistant. Your final response MUST be in {native_language_name}.
    Analyze all the following information to provide a helpful and actionable solution. For every statement or recommendation you make, provide the reasoning behind it based on the user's context.

    Farmer's Profile: {profile}
    Today's Predictions: {predictions}
    Analysis of Uploaded Image: {image_analysis}
    Relevant Knowledge (in English): {rag_context}
    Farmer's Question (translated to English): "{eng_query}"

    Based on all the above information, provide a comprehensive answer in {native_language_name}.
    
    The answer has to be to the point only answering the given {eng_query} question only. No extra information. Only answer the asked question and give a small to the point reasoning for the same no extra analysis. Provide everything in proper markdown.
    """
    
    response = llm_model.generate_content(prompt)
    
    return response.text