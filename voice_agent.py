import streamlit as st
from gtts import gTTS
import openai
import os
import tempfile
import time

openai.api_key = os.getenv("OPENAI_API_KEY")

def transcribe_audio(file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
        tmp_file.write(file.read())
        tmp_path = tmp_file.name

    with open(tmp_path, "rb") as audio_file:
        transcript = openai.Audio.transcribe("whisper-1", audio_file)

    os.remove(tmp_path)
    return transcript['text']

def speak(text):
    tts = gTTS(text)
    output_path = "output.mp3"
    tts.save(output_path)
    return output_path

def voice_agent_ui():
    st.header("🎤 Voice Agent: Ask Your Market Brief")

    audio_file = st.file_uploader("Upload a question (MP3 or WAV)", type=["mp3", "wav"])

    if audio_file is not None:
        with st.spinner("Transcribing..."):
            question = transcribe_audio(audio_file)
            st.success("Transcription complete!")
            st.write(f"🗣️ You asked: `{question}`")

            # Here you can pass the `question` to your orchestrator or LLM pipeline
            # For demo purposes, let's mock a response:
            response = f"Mocked response to: {question}"

            st.write(f"💬 Assistant says: {response}")

            audio_path = speak(response)
            audio_bytes = open(audio_path, 'rb').read()
            st.audio(audio_bytes, format='audio/mp3')
