# utils/translation_utils.py
import google.generativeai as genai
# --- CORRECTED IMPORT ---
# Import the config module from the parent package
from krishisakhi_api import config

# utils/translation_utils.py
import google.generativeai as genai
from krishisakhi_api import config

genai.configure(api_key=config.GEMINI_API_KEY)
translation_model = genai.GenerativeModel(
    config.MODEL_NAME
)

# ... (the rest of your translate_text function remains the same)

def translate_text(text: str, src: str, dest: str) -> str:
    """Translates text with detailed logging."""
    # --- UPDATED USAGE ---
    src_lang_name = config.SUPPORTED_LANGUAGES.get(src, src)
    dest_lang_name = config.SUPPORTED_LANGUAGES.get(dest, dest)
    
    print(f"[TRANSLATE] Translating from '{src_lang_name}' to '{dest_lang_name}': '{text[:50]}...'")
    try:
        if src == dest:
            print("[TRANSLATE] Source and destination languages are the same. Skipping.")
            return text

        prompt = f"Translate the following text from {src_lang_name} to {dest_lang_name}. Respond with only the translated text:\n\n{text}"
        response = translation_model.generate_content(prompt)
        translated_text = response.text.strip()
        print(f"[TRANSLATE] Success. Result: '{translated_text[:50]}...'")
        return translated_text
    except Exception as e:
        print(f"❌ ERROR [TRANSLATE]: Failed to translate text. Reason: {e}")
        return "Translation Error"