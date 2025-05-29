import streamlit as st
import requests
import json
import sounddevice as sd
import soundfile as sf
import numpy as np
from datetime import datetime
import pytz
import time
from pathlib import Path
import io
import base64
import tempfile
from pydub import AudioSegment
from pydub.playback import play

# Configure page
st.set_page_config(
    page_title="Multi-Agent Finance Assistant",
    page_icon="📈",
    layout="wide"
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "recording" not in st.session_state:
    st.session_state.recording = False
if "audio_data" not in st.session_state:
    st.session_state.audio_data = None

# API endpoint and configuration
API_URL = "http://localhost:8000"
API_TIMEOUT = 60  # 60 seconds timeout
MAX_RETRIES = 3   # Maximum number of retries
RETRY_DELAY = 1   # Delay between retries in seconds

def make_api_request(endpoint, method="get", data=None, timeout=API_TIMEOUT, max_retries=MAX_RETRIES):
    """Make API request with retry logic"""
    for attempt in range(max_retries):
        try:
            if method.lower() == "get":
                response = requests.get(f"{API_URL}/{endpoint}", timeout=timeout)
            else:
                response = requests.post(f"{API_URL}/{endpoint}", json=data, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.Timeout:
            if attempt == max_retries - 1:
                st.error(f"Cannot connect to API service: Request timed out after {max_retries} attempts")
                return None
            time.sleep(RETRY_DELAY * (attempt + 1))
        except requests.RequestException as e:
            if attempt == max_retries - 1:
                st.error(f"Cannot connect to API service: {str(e)}")
                return None
            time.sleep(RETRY_DELAY * (attempt + 1))

def record_audio(duration=5):
    """Record audio from microphone"""
    sample_rate = 16000
    recording = sd.rec(int(duration * sample_rate),
                      samplerate=sample_rate,
                      channels=1,
                      dtype=np.float32)
    sd.wait()
    return recording.flatten()

def save_audio(audio_data, path):
    """Save audio data to file"""
    sf.write(path, audio_data, 16000)

def play_audio(audio_data):
    """Play audio data"""
    sd.play(audio_data, 16000)
    sd.wait()

def play_base64_audio(audio_base64):
    """Play audio from base64 string using Streamlit's native audio player"""
    try:
        # Decode base64 to bytes
        audio_bytes = base64.b64decode(audio_base64)
        
        # Create temp directory if it doesn't exist
        temp_dir = Path("temp_audio")
        temp_dir.mkdir(exist_ok=True)
        
        # Save to temporary file with unique name
        temp_file_path = temp_dir / f"temp_audio_{int(time.time())}.mp3"
        temp_file_path.write_bytes(audio_bytes)
        
        # Display audio in Streamlit
        st.audio(str(temp_file_path))
        
        # Clean up temp file
        temp_file_path.unlink()
        
    except Exception as e:
        st.error(f"Error playing audio: {str(e)}")

def get_current_time_est():
    """Get current time in EST"""
    est = pytz.timezone('US/Eastern')
    return datetime.now(est)

# Sidebar
st.sidebar.title("Settings")
voice_enabled = st.sidebar.checkbox("Enable Voice Input/Output", value=True)
auto_brief = st.sidebar.checkbox("Enable Auto Morning Brief", value=True)

# Main content
st.title("Multi-Agent Finance Assistant 📈")

# System status check
status = make_api_request("health")
if status and status.get("status") == "operational":
    st.sidebar.success("✅ All Systems Operational")
    
    # Display component status
    st.sidebar.markdown("Component Status:")
    for component, status in status.get("components", {}).items():
        if status:
            st.sidebar.markdown(f"✅ {component}")
        else:
            st.sidebar.markdown(f"❌ {component}")
else:
    st.sidebar.error("❌ System Status Check Failed")

# Morning market brief
st.header("Morning Market Brief")
est_time = datetime.now(pytz.timezone('US/Eastern'))
st.subheader(f"Current Time: {est_time.strftime('%I:%M %p EST')}")

brief = make_api_request("morning-brief")
if brief:
    st.markdown(brief.get("text_response", "No morning brief available"))
    st.success("Morning Brief Received!")

# Custom market query
st.header("Custom Market Query")
query = st.text_input("Enter your market query:")

if query:
    # Prepare request data
    request_data = {
        "query": query,
        "voice_input": None,
        "require_voice_response": True
    }
    
    # Make API request
    response = make_api_request("analyze", method="post", data=request_data)
    
    if response:
        # Display text response
        st.markdown(response.get("text_response", "No response available"))
        
        # Handle voice response if available
        voice_response = response.get("voice_response")
        if voice_response and voice_response.get("audio_data"):
            st.audio(base64.b64decode(voice_response["audio_data"]), format=voice_response["format"])

# Display conversation history
st.header("Conversation History")
for msg in st.session_state.messages:
    st.markdown(msg)
