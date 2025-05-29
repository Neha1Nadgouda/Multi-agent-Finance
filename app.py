import streamlit as st
import requests
import json
from datetime import datetime
import pytz
import time
import base64
from pathlib import Path
from voice_agent import voice_agent_ui

# ---------------------------
# ✅ App page config FIRST
# ---------------------------
st.set_page_config(
    page_title="Multi-Agent Finance Assistant",
    page_icon="📈",
    layout="wide"
)

# ---------------------------
# ✅ Run the voice interface UI AFTER page config
# ---------------------------
voice_agent_ui()

# ---------------------------
# Session state
# ---------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

# ---------------------------
# API configuration
# ---------------------------
API_URL = "http://localhost:8000"  # Use your backend URL or deployed URL
API_TIMEOUT = 60
MAX_RETRIES = 3
RETRY_DELAY = 1

# ---------------------------
# API call logic
# ---------------------------
def make_api_request(endpoint, method="get", data=None, timeout=API_TIMEOUT, max_retries=MAX_RETRIES):
    for attempt in range(max_retries):
        try:
            if method.lower() == "get":
                response = requests.get(f"{API_URL}/{endpoint}", timeout=timeout)
            else:
                response = requests.post(f"{API_URL}/{endpoint}", json=data, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            if attempt == max_retries - 1:
                st.error(f"API error: {str(e)}")
            time.sleep(RETRY_DELAY * (attempt + 1))

# ---------------------------
# Sidebar
# ---------------------------
st.sidebar.title("Settings")
voice_enabled = st.sidebar.checkbox("Enable Voice Input/Output", value=True)
auto_brief = st.sidebar.checkbox("Enable Auto Morning Brief", value=True)

# ---------------------------
# Health check
# ---------------------------
st.sidebar.markdown("### System Status")
status = make_api_request("health")
if status and status.get("status") == "operational":
    st.sidebar.success("✅ All Systems Operational")
    for component, online in status.get("components", {}).items():
        st.sidebar.markdown(f"{'✅' if online else '❌'} {component}")
else:
    st.sidebar.error("❌ API Offline or Failed")

# ---------------------------
# Morning Brief
# ---------------------------
st.header("🌅 Morning Market Brief")
est_time = datetime.now(pytz.timezone('US/Eastern'))
st.markdown(f"**Current Time (EST):** {est_time.strftime('%I:%M %p')}")

brief = make_api_request("morning-brief")
if brief:
    st.success("Brief Received:")
    st.markdown(brief.get("text_response", "No brief found."))

# ---------------------------
# Custom Market Query
# ---------------------------
st.header("🔍 Custom Market Query")
query = st.text_input("Ask your question:")

if query:
    request_data = {
        "query": query,
        "voice_input": None,
        "require_voice_response": True
    }
    response = make_api_request("analyze", method="post", data=request_data)
    if response:
        st.markdown(response.get("text_response", "No response."))
        voice = response.get("voice_response", {})
        if voice and voice.get("audio_data"):
            st.audio(base64.b64decode(voice["audio_data"]), format=voice["format"])

# ---------------------------
# Conversation History
# ---------------------------
st.header("🗃️ Conversation History")
for msg in st.session_state.messages:
    st.markdown(msg)
