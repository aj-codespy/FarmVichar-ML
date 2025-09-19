import streamlit as st
import requests
import json
import os

# Configuration
LOCAL_API_BASE = os.environ.get("LOCAL_API_BASE", "http://127.0.0.1:8000")
EXTERNAL_API_BASE = os.environ.get("EXTERNAL_API_BASE", "https://api-krishisakhi.onrender.com")
TEST_USER_PATH = os.path.join(os.path.dirname(__file__), "test_user.json")

st.set_page_config(page_title="KrishiSakhi API Tester", layout="centered")
st.title("KrishiSakhi API Tester")

# Load test user
with open(TEST_USER_PATH, "r", encoding="utf-8") as f:
    TEST_USER = json.load(f)

st.subheader("1) Login to External Auth API")
st.caption("POST /api/auth/login")

if st.button("Login as Test User"):
    try:
        login_url = f"{EXTERNAL_API_BASE}/api/auth/login"
        payload = {"name": TEST_USER.get("name", ""), "phone": TEST_USER["phone"], "password": TEST_USER["password"]}
        resp = requests.post(login_url, json=payload, timeout=15)
        st.write({"status_code": resp.status_code})
        try:
            data = resp.json()
        except Exception:
            data = {"text": resp.text}
        st.write(data)
        if resp.ok and isinstance(data, dict):
            st.session_state["access_token"] = data.get("access_token") or data.get("token")
            # Map "user_id" to access token semantics for local API per new rule
            st.session_state["user_id"] = st.session_state.get("access_token") or data.get("user", {}).get("id") or data.get("farm_id") or TEST_USER.get("phone")
            st.success("Login stored in session_state.")
    except Exception as e:
        st.error(f"Login failed: {e}")

st.divider()
st.subheader("2) Test Local APIs (token-based, no user_id in paths)")
access_token = st.session_state.get("access_token")
auth_headers = {"Authorization": f"Bearer {access_token}"} if access_token else {}

col1, col2, col3 = st.columns(3)
with col1:
    if st.button("GET /dashboard"):
        try:
            url = f"{LOCAL_API_BASE}/dashboard"
            r = requests.get(url, headers=auth_headers, timeout=30)
            st.write({"status_code": r.status_code})
            st.json(r.json() if r.headers.get("content-type", "").startswith("application/json") else {"text": r.text})
        except Exception as e:
            st.error(e)

with col2:
    if st.button("GET /weather"):
        try:
            url = f"{LOCAL_API_BASE}/weather"
            r = requests.get(url, headers=auth_headers, timeout=15)
            st.write({"status_code": r.status_code})
            st.json(r.json() if r.headers.get("content-type", "").startswith("application/json") else {"text": r.text})
        except Exception as e:
            st.error(e)

with col3:
    if st.button("GET /alerts"):
        try:
            url = f"{LOCAL_API_BASE}/alerts"
            r = requests.get(url, headers=auth_headers, timeout=15)
            st.write({"status_code": r.status_code})
            st.json(r.json() if r.headers.get("content-type", "").startswith("application/json") else {"text": r.text})
        except Exception as e:
            st.error(e)

st.markdown("---")
st.subheader("Chat: POST /chat")
text_query = st.text_input("Text query", "What should I do about pest control this week?")
image_file = st.file_uploader("Optional image", type=["jpg", "jpeg", "png"])
audio_file = st.file_uploader("Optional audio", type=["wav", "mp3", "ogg", "flac"])

if st.button("Send Chat"):
    try:
        url = f"{LOCAL_API_BASE}/chat"
        files = {}
        data = {"text_query": text_query}
        if image_file is not None:
            files["image_file"] = (image_file.name, image_file.getvalue(), image_file.type or "image/png")
        if audio_file is not None:
            files["audio_file"] = (audio_file.name, audio_file.getvalue(), audio_file.type or "audio/wav")
        r = requests.post(url, data=data, files=files or None, headers=auth_headers, timeout=120)
        st.write({"status_code": r.status_code})
        st.json(r.json() if r.headers.get("content-type", "").startswith("application/json") else {"text": r.text})
    except Exception as e:
        st.error(e)

st.markdown("---")
st.subheader("Logs: POST /logs")

default_log = {
    "log_type": "Pest Sighting",
    "date": "2025-09-16",
    "crop_name": "Rice",
    "notes": "Saw whiteflies on leaves",
    "details": {"severity": "medium"}
}
log_json_text = st.text_area("Log JSON", json.dumps(default_log, indent=2))
if st.button("Submit Log"):
    try:
        log_obj = json.loads(log_json_text)
        url = f"{LOCAL_API_BASE}/logs"
        r = requests.post(url, json=log_obj, headers=auth_headers, timeout=30)
        st.write({"status_code": r.status_code})
        st.json(r.json() if r.headers.get("content-type", "").startswith("application/json") else {"text": r.text})
    except Exception as e:
        st.error(e)

st.markdown("---")
st.subheader("Voice Log: POST /logs/voice")
voice_audio = st.file_uploader("Upload voice log audio", key="voice", type=["wav", "mp3", "ogg", "flac"])
if st.button("Submit Voice Log"):
    try:
        if not voice_audio:
            st.warning("Please upload an audio file first.")
        else:
            url = f"{LOCAL_API_BASE}/logs/voice"
            files = {"audio_file": (voice_audio.name, voice_audio.getvalue(), voice_audio.type or "audio/wav")}
            r = requests.post(url, files=files, headers=auth_headers, timeout=120)
            st.write({"status_code": r.status_code})
            st.json(r.json() if r.headers.get("content-type", "").startswith("application/json") else {"text": r.text})
    except Exception as e:
        st.error(e)

st.markdown("---")
st.subheader("Onboarding Voice: POST /onboarding/voice")
context_q = st.text_input("Context question", "What is your name?")
field_name = st.text_input("Field name", "full_name")
onboard_audio = st.file_uploader("Upload onboarding audio", key="onboard", type=["wav", "mp3", "ogg", "flac"])
if st.button("Submit Onboarding Voice"):
    try:
        if not onboard_audio:
            st.warning("Please upload an audio file first.")
        else:
            url = f"{LOCAL_API_BASE}/onboarding/voice"
            files = {"audio_file": (onboard_audio.name, onboard_audio.getvalue(), onboard_audio.type or "audio/wav")}
            data = {"context_question": context_q, "field_name": field_name}
            r = requests.post(url, data=data, files=files, headers=auth_headers, timeout=120)
            st.write({"status_code": r.status_code})
            st.json(r.json() if r.headers.get("content-type", "").startswith("application/json") else {"text": r.text})
    except Exception as e:
        st.error(e)

st.info("Set LOCAL_API_BASE and EXTERNAL_API_BASE env vars if needed.")

st.markdown("\n---\n")
st.subheader("3) External Backend Management (Farms/Alerts) - Token Required")

# ---- Helper functions for external API ----
def ext_register_user(user_data: dict):
    url = f"{EXTERNAL_API_BASE}/api/auth/register"
    r = requests.post(url, json=user_data, timeout=20)
    r.raise_for_status()
    return r.json()

def ext_login_user(credentials: dict):
    url = f"{EXTERNAL_API_BASE}/api/auth/login"
    # Some backends require name even on login; include if provided
    body = {k: v for k, v in credentials.items() if k in ("name", "phone", "password", "phone_number", "mobile")}
    r = requests.post(url, json=body, timeout=20)
    r.raise_for_status()
    return r.json()

def ext_create_farm(token: str, farm_data: dict):
    url = f"{EXTERNAL_API_BASE}/api/farms/"
    r = requests.post(url, headers={"Authorization": f"Bearer {token}"}, json=farm_data, timeout=20)
    r.raise_for_status()
    return r.json()

def ext_get_all_farms(token: str):
    url = f"{EXTERNAL_API_BASE}/api/farms/"
    r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=20)
    r.raise_for_status()
    return r.json()

def ext_update_farm(token: str, farm_id: str, update_data: dict):
    url = f"{EXTERNAL_API_BASE}/api/farms/{farm_id}"
    r = requests.patch(url, headers={"Authorization": f"Bearer {token}"}, json=update_data, timeout=20)
    r.raise_for_status()
    return r.json()

def ext_log_activity(token: str, farm_id: str, activity_data: dict):
    url = f"{EXTERNAL_API_BASE}/api/farms/{farm_id}/activities"
    r = requests.post(url, headers={"Authorization": f"Bearer {token}"}, json=activity_data, timeout=20)
    r.raise_for_status()
    return r.json()

def ext_get_farm_with_activities(token: str, farm_id: str):
    url = f"{EXTERNAL_API_BASE}/api/farms/{farm_id}"
    r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=20)
    r.raise_for_status()
    return r.json()

def ext_create_alert(token: str, alert_data: dict):
    url = f"{EXTERNAL_API_BASE}/api/alerts/"
    r = requests.post(url, headers={"Authorization": f"Bearer {token}"}, json=alert_data, timeout=20)
    r.raise_for_status()
    return r.json()

def ext_get_all_alerts(token: str):
    url = f"{EXTERNAL_API_BASE}/api/alerts/"
    r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=20)
    r.raise_for_status()
    return r.json()

def ext_mark_alert_as_seen(token: str, alert_id: str):
    url = f"{EXTERNAL_API_BASE}/api/alerts/{alert_id}/seen"
    r = requests.patch(url, headers={"Authorization": f"Bearer {token}"}, timeout=20)
    r.raise_for_status()
    return {"seen": True}

with st.expander("Auth (Register/Login)"):
    colA, colB = st.columns(2)
    with colA:
        st.caption("POST /api/auth/register")
        reg_name = st.text_input("Name", "Comprehensive Test User")
        reg_phone = st.text_input("Phone", "9XXXXXXXXX")
        reg_password = st.text_input("Password", "password123")
        if st.button("Register User"):
            try:
                out = ext_register_user({"name": reg_name, "phone": reg_phone, "password": reg_password})
                st.json(out)
            except Exception as e:
                st.error(e)
    with colB:
        st.caption("POST /api/auth/login")
        login_name = st.text_input("Login Name (if required)", TEST_USER.get("name", ""))
        login_phone = st.text_input("Login Phone", TEST_USER.get("phone", ""))
        login_password = st.text_input("Login Password", TEST_USER.get("password", ""))
        if st.button("Login and Save Token"):
            try:
                out = ext_login_user({"name": login_name, "phone": login_phone, "password": login_password})
                st.json(out)
                st.session_state["access_token"] = out.get("access_token") or out.get("token")
                st.success("Token saved to session.")
            except Exception as e:
                st.error(e)

with st.expander("Farms"):
    token = st.session_state.get("access_token")
    if not token:
        st.warning("Login first to obtain a token.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            st.caption("POST /api/farms/")
            farm_payload_text = st.text_area("Create Farm JSON", json.dumps({
                "farmName": "Automated Test Farm",
                "location": {"latitude": 10.1234, "longitude": 76.5432},
                "area": 2.5,
                "soilType": "Alluvial"
            }, indent=2))
            if st.button("Create Farm"):
                try:
                    out = ext_create_farm(token, json.loads(farm_payload_text))
                    st.json(out)
                except Exception as e:
                    st.error(e)
        with col2:
            st.caption("GET /api/farms/")
            if st.button("List My Farms"):
                try:
                    out = ext_get_all_farms(token)
                    st.json(out)
                except Exception as e:
                    st.error(e)
        st.markdown("---")
        col3, col4 = st.columns(2)
        with col3:
            st.caption("PATCH /api/farms/{farm_id}")
            upd_farm_id = st.text_input("Farm ID to update", "")
            upd_payload_text = st.text_area("Update JSON", json.dumps({"area": 3.0}, indent=2))
            if st.button("Update Farm"):
                try:
                    out = ext_update_farm(token, upd_farm_id, json.loads(upd_payload_text))
                    st.json(out)
                except Exception as e:
                    st.error(e)
        with col4:
            st.caption("POST /api/farms/{farm_id}/activities")
            act_farm_id = st.text_input("Farm ID for activity", "")
            act_payload_text = st.text_area("Activity JSON", json.dumps({"type": "Sowing", "description": "Sowed seeds."}, indent=2))
            if st.button("Log Activity"):
                try:
                    out = ext_log_activity(token, act_farm_id, json.loads(act_payload_text))
                    st.json(out)
                except Exception as e:
                    st.error(e)
        st.markdown("---")
        st.caption("GET /api/farms/{farm_id}")
        det_farm_id = st.text_input("Farm ID (details)", "")
        if st.button("Get Farm With Activities"):
            try:
                out = ext_get_farm_with_activities(token, det_farm_id)
                st.json(out)
            except Exception as e:
                st.error(e)

with st.expander("Alerts"):
    token = st.session_state.get("access_token")
    if not token:
        st.warning("Login first to obtain a token.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            st.caption("POST /api/alerts/")
            alert_payload_text = st.text_area("Alert JSON", json.dumps({"type": "System", "title": "Test", "message": "Hello"}, indent=2))
            if st.button("Create Alert"):
                try:
                    out = ext_create_alert(token, json.loads(alert_payload_text))
                    st.json(out)
                except Exception as e:
                    st.error(e)
        with col2:
            st.caption("GET /api/alerts/")
            if st.button("List Alerts"):
                try:
                    out = ext_get_all_alerts(token)
                    st.json(out)
                except Exception as e:
                    st.error(e)
        st.markdown("---")
        st.caption("PATCH /api/alerts/{alert_id}/seen")
        seen_alert_id = st.text_input("Alert ID to mark seen", "")
        if st.button("Mark Alert as Seen"):
            try:
                out = ext_mark_alert_as_seen(token, seen_alert_id)
                st.json(out)
            except Exception as e:
                st.error(e)

