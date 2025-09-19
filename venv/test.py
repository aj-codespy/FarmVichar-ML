import streamlit as st
from google.cloud import speech
from google.oauth2 import service_account # <-- NEW: Import service_account

# --- Path to your downloaded key file ---
# Replace this with the actual path to your JSON key file.
KEY_FILE_PATH = "keys.json" 

st.title("Voice to Text with Google API")
audio_file = st.file_uploader("Upload audio file (e.g., .wav, .ogg)", type=["wav", "ogg", "mp3", "flac"])

if audio_file and st.button("Transcribe"):
    st.info("Sending audio to Google Cloud for transcription...")

    try:
        # --- NEW: Load credentials directly from the file ---
        credentials = service_account.Credentials.from_service_account_file(KEY_FILE_PATH)
        
        # --- UPDATED: Pass the credentials to the client ---
        client = speech.SpeechClient(credentials=credentials)

        # 2. Read the audio file's content
        content = audio_file.read()
        audio = speech.RecognitionAudio(content=content)

        # 3. Configure the recognition request
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.OGG_OPUS,
            sample_rate_hertz=16000,
            language_code="mr-IN",  # "ml-IN" for Malayalam, "mr-IN" for Marathi
            enable_automatic_punctuation=True
        )

        # 4. Perform the recognition
        response = client.recognize(config=config, audio=audio)
        
        # 5. Extract and display the transcript
        if response.results:
            transcript = response.results[0].alternatives[0].transcript
            st.success("Transcription Complete!")
            st.write("Transcription:", transcript)
        else:
            st.warning("No speech could be recognized in the audio.")

    except FileNotFoundError:
        st.error(f"Authentication Error: The key file was not found at '{KEY_FILE_PATH}'.")
        st.error("Please make sure the key file is in the correct location.")
    except Exception as e:
        st.error(f"An error occurred with the Google Speech-to-Text API:")
        st.error(e)