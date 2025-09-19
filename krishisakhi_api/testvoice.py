import streamlit as st
import config
from google.cloud import speech
from google.oauth2 import service_account
import google.generativeai as genai

# --- Client Initialization (Cached for performance) ---
@st.cache_resource
def get_clients():
    """Initializes and returns the Google Cloud clients."""
    try:
        # 1. Initialize Google Speech-to-Text Client
        speech_credentials = service_account.Credentials.from_service_account_file(config.GOOGLE_KEY_FILE_PATH)
        speech_client = speech.SpeechClient(credentials=speech_credentials)
        
        # 2. Initialize Google Gemini Client for translation
        genai.configure(api_key=config.GEMINI_API_KEY)
        translation_model = genai.GenerativeModel('gemini-1.5-flash')
        
        print("✅ AI clients loaded successfully.")
        return speech_client, translation_model
    except Exception as e:
        st.error(f"Error initializing Google Cloud clients: {e}")
        st.error("Please ensure your 'keys.json' and GEMINI_API_KEY are correct.")
        return None, None

speech_client, translation_model = get_clients()

# --- Main App UI ---
st.title("Multilingual Voice Transcription & Translation")
st.write("Upload an audio file in your selected language to get the transcription and its English translation.")

if speech_client and translation_model:
    # --- User Inputs ---
    language_code = st.selectbox(
        "Select the language spoken in the audio file:",
        options=list(config.SUPPORTED_LANGUAGES.keys()),
        format_func=lambda code: config.SUPPORTED_LANGUAGES[code]
    )

    audio_file = st.file_uploader("Upload your audio file", type=["wav", "ogg", "mp3", "flac"])

    if audio_file is not None and st.button("Process Audio"):
        st.audio(audio_file, format='audio/ogg')
        
        audio_bytes = audio_file.read()

        # --- Step 1: Transcription ---
        with st.spinner("Transcribing audio in its native language..."):
            try:
                audio = speech.RecognitionAudio(content=audio_bytes)
                recognition_config = speech.RecognitionConfig(
                    # Example encoding, may need adjustment for different file types
                    encoding=speech.RecognitionConfig.AudioEncoding.OGG_OPUS, 
                    sample_rate_hertz=16000,
                    language_code=f"{language_code}-IN",
                    enable_automatic_punctuation=True
                )
                
                response = speech_client.recognize(config=recognition_config, audio=audio)
                
                if not response.results:
                    st.warning("Could not transcribe any speech from the audio file.")
                else:
                    transcribed_text = response.results[0].alternatives[0].transcript
                    st.success("Transcription Complete!")
                    st.subheader(f"Detected Text ({config.SUPPORTED_LANGUAGES[language_code]}):")
                    st.write(transcribed_text)
                    
                    # --- Step 2: Translation ---
                    with st.spinner("Translating text to English..."):
                        prompt = f"Translate the following {config.SUPPORTED_LANGUAGES[language_code]} text to English: '{transcribed_text}'"
                        translation_response = translation_model.generate_content(prompt)
                        translated_text = translation_response.text.strip()
                        
                        st.success("Translation Complete!")
                        st.subheader("English Translation:")
                        st.write(translated_text)

            except Exception as e:
                st.error(f"An error occurred during processing: {e}")
else:
    st.error("Application is not configured correctly. Please check the server logs.")