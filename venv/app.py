# app.py
import streamlit as st
import json
import pandas as pd
from pathlib import Path
import plotly.graph_objects as go
import base64

# Import utility functions from your project
from utils.chatbot_utils import process_chat_query, analyze_image_with_gemini
from utils.rag_utils import load_faiss_index
from utils.translation_utils import translate_text
import config

# --- Page Configuration ---
st.set_page_config(
    page_title="Krishi Sakhi",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Global State and Data Loading ---
@st.cache_resource
def load_resources():
    """Load all necessary data and models once."""
    base_path = Path(__file__).parent
    
    try:
        with open(base_path / "demo_data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        st.error("FATAL: demo_data.json not found. Please ensure it's in the same directory as app.py.")
        st.stop()
    
    faiss_index, docs = load_faiss_index(
        str(base_path / config.VECTOR_DB_PATH), 
        str(base_path / config.DOCS_PATH)
    )
    if faiss_index is None:
        st.warning("Warning: FAISS index not found. The chatbot may not have full knowledge.")
    
    return data, faiss_index, docs

# --- Initialize App State ---
if 'app_data' not in st.session_state:
    app_data, faiss_index, docs = load_resources()
    st.session_state.app_data = app_data
    st.session_state.faiss_index = faiss_index
    st.session_state.docs = docs
    st.session_state.messages = []

# --- UI Helper Functions ---
def create_gauge_chart(value, title, max_value):
    """Creates a Plotly gauge chart."""
    return go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={'text': title, 'font': {'size': 20}},
        gauge={
            'axis': {'range': [0, max_value]},
            'bar': {'color': "#2E8B57"},
        }
    ))

# --- Data Access ---
USER_PROFILE = st.session_state.app_data["user"]["farm"]
PERSONAL_INFO = st.session_state.app_data["user"]["farm"]["extraData"]["personal_info"]
PREDICTIONS = st.session_state.app_data["dashboard_predictions"]
WEATHER = st.session_state.app_data["weather"]

# --- Main Application ---
st.title(f"🌾 Krishi Sakhi Dashboard for {PERSONAL_INFO['full_name']}")
st.caption(f"Location: {USER_PROFILE['extraData']['location_details']['village']}, Kerala | Today: September 17, 2025")

# --- Sidebar for Language Selection ---
st.sidebar.title("Settings")
selected_language = st.sidebar.selectbox(
    "Choose Language", 
    options=list(config.SUPPORTED_LANGUAGES.keys()),
    format_func=lambda x: config.SUPPORTED_LANGUAGES[x],
    index=list(config.SUPPORTED_LANGUAGES.keys()).index(st.session_state.app_data["user"]["preferences"]["language_code"])
)
st.session_state.app_data["user"]["preferences"]["language_code"] = selected_language


# --- Main Tabs ---
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "💬 Chat with Krishi Sakhi", "🖼️ Image Analysis", "🔔 Alerts"])

# --- Dashboard Tab ---
with tab1:
    st.header("Today's Overview")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Weather")
        st.metric("Temperature", f"{WEATHER['temperature']} °C")
        st.metric("Condition", WEATHER['weather'])
        st.metric("Humidity", f"{WEATHER['humidity']}%")

    with col2:
        st.subheader("Farmer Profile")
        st.text(f"Name: {PERSONAL_INFO['full_name']}")
        st.text(f"Location: {USER_PROFILE['extraData']['location_details']['village']}")
        st.text(f"Primary Crop: {USER_PROFILE['extraData']['cultivation_details']['current_crops'][0]}")

    st.divider()
    
    st.header("AI Predictions & Recommendations")
    col3, col4, col5 = st.columns(3)
    with col3:
        fig = create_gauge_chart(PREDICTIONS['pest_risk_percent'], "Pest Risk", 100)
        st.plotly_chart(fig, use_container_width=True)
    with col4:
        fig = create_gauge_chart(PREDICTIONS['quality_grading_score'], "Quality Grading Score", 100)
        st.plotly_chart(fig, use_container_width=True)
    with col5:
        st.metric("Recommended Crop", PREDICTIONS['recommended_crop'])
        st.metric("Yield Prediction", f"{PREDICTIONS['yield_prediction_kg_acre']} kg/acre")

    st.divider()

    col6, col7 = st.columns(2)
    with col6:
        st.subheader("Market Price Outlook")
        price_range = PREDICTIONS['price_range_per_quintal']
        st.success(f"Estimated Price for {price_range['crop_name']}: ₹{price_range['min_price']} - ₹{price_range['max_price']} per quintal")

    with col7:
        st.subheader("Government Schemes")
        st.write("**Applicable Schemes:**")
        for scheme in PREDICTIONS['applicable_schemes']: st.info(scheme)
        st.write("**Applied Schemes:**")
        for scheme in PREDICTIONS['applied_schemes']: st.success(scheme)

# --- Chat Tab ---
with tab2:
    st.header("Chat with your AI Assistant")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Combined input area for text and voice
    text_prompt = st.text_input("Ask a question in text...", key="text_input")
    audio_file = st.file_uploader("Or upload your question as a voice note...", type=["wav", "ogg", "mp3"])

    if st.button("Send Message", key="send_chat"):
        user_input_content = ""
        final_query = ""

        if audio_file:
            st.info("Processing voice note...")
            # Mock transcription for demo purposes
            transcribed_text = "How to manage stem borer in my rice crop?"
            final_query = transcribed_text
            user_input_content = f"🎤 Voice Note: *'{transcribed_text}'*"
            st.audio(audio_file.getvalue())
        elif text_prompt:
            final_query = text_prompt
            user_input_content = text_prompt

        if final_query:
            st.session_state.messages.append({"role": "user", "content": user_input_content})
            with st.chat_message("user"):
                st.markdown(user_input_content)

            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    response = process_chat_query(
                        query=final_query,
                        profile=USER_PROFILE,
                        predictions=PREDICTIONS,
                        faiss_index=st.session_state.faiss_index,
                        docs=st.session_state.docs,
                        language=selected_language,
                        image_bytes=None
                    )
                    st.markdown(response)
            
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.rerun()

# --- Image Analysis Tab ---
with tab3:
    st.header("Analyze Crop Health from an Image")
    uploaded_file = st.file_uploader("Upload an image of your crop", type=["png", "jpg", "jpeg"])

    if uploaded_file is not None:
        bytes_data = uploaded_file.getvalue()
        st.image(bytes_data, caption='Uploaded Image.', use_column_width=True)
        
        with st.spinner("Analyzing image..."):
            analysis_result = analyze_image_with_gemini(bytes_data)
            st.subheader("AI Analysis Result:")
            st.write(analysis_result)

# --- NEW: Alerts Tab ---
with tab4:
    st.header("Notifications & Alerts")

    # This section uses static data for the demo.
    # In a real app, this would come from the /alerts API endpoint.
    
    st.warning("**High Priority Alert: Pest Risk**")
    st.write(f"""
    - **Risk Level**: High ({PREDICTIONS['pest_risk_percent']}%)
    - **Details**: Our AI model predicts a high probability of a **Rice Stem Borer** outbreak in the Kizhakkencherry area this week due to favorable weather conditions.
    - **Suggestion**: Proactively apply a neem oil solution or consult the chatbot for specific organic pesticide recommendations.
    """)

    st.info("**Medium Priority Alert: Weather Advisory**")
    st.write(f"""
    - **Event**: Moderate rainfall expected in 2 days.
    - **Details**: The IMD forecast indicates a 70% chance of 10-15mm of rain.
    - **Suggestion**: Consider postponing your next irrigation cycle to conserve water and prevent waterlogging.
    """)

    st.success("**Scheme Information**")
    st.write(f"""
    - **Scheme**: Pradhan Mantri Fasal Bima Yojana (PMFBY)
    - **Details**: The deadline to enroll for crop insurance for the Rabi season is approaching.
    - **Suggestion**: Visit the chatbot and ask "How to apply for PMFBY" to get a step-by-step guide.
    """)