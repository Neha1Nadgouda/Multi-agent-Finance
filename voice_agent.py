"""Voice Agent for speech-to-text and text-to-speech conversion"""
from typing import Dict, Any, Optional
from datetime import datetime
import os
from dotenv import load_dotenv
import openai
import base64
import tempfile

load_dotenv()

class VoiceAgent:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        openai.api_key = self.api_key

    async def speech_to_text(self, audio_data: bytes) -> str:
        """Convert speech to text using OpenAI's API"""
        try:
            # Save audio data to a temporary file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name

            # Transcribe using OpenAI's API
            with open(temp_file_path, "rb") as audio_file:
                transcript = openai.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text"
                )

            # Clean up temporary file
            os.unlink(temp_file_path)
            
            return transcript
            
        except Exception as e:
            print(f"Error in speech to text conversion: {str(e)}")
            return "Could not transcribe audio. Please try again."

    async def text_to_speech(self, text: str) -> Dict[str, Any]:
        """Convert text to speech using OpenAI's API"""
        try:
            # Ensure text is not empty and within limits
            if not text or len(text) > 4096:
                raise ValueError("Text must be between 1 and 4096 characters")

            # Generate speech with enhanced quality settings
            response = openai.audio.speech.create(
                model="tts-1",
                voice="nova",  # Using nova voice for better clarity
                input=text,
                speed=0.9,  # Slightly slower for better clarity
                response_format="mp3"  # Using mp3 for better quality/size ratio
            )
            
            if not response or not response.content:
                raise ValueError("No audio data received from API")

            # Get the speech audio in bytes and encode as base64
            audio_data = response.content
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            return {
                "audio_data": audio_base64,
                "format": "audio/mp3",  # Updated format to match response_format
                "encoding": "base64",
                "content_length": len(audio_data)
            }
            
        except Exception as e:
            print(f"Error in text to speech conversion: {str(e)}")
            return {
                "error": str(e),
                "audio_data": None,
                "format": None,
                "encoding": None
            }

    async def health_check(self) -> Dict[str, Any]:
        """Check if the voice service is working"""
        try:
            # Test text-to-speech with a short message
            test_response = await self.text_to_speech("Test message")
            
            return {
                "healthy": test_response.get("audio_data") is not None,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            } 