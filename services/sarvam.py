import base64
import os
import subprocess
import tempfile
import httpx
from config import SARVAM_API_KEY

SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"
SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"


def transcribe(audio_bytes: bytes, filename: str = "audio.wav") -> str:
    with httpx.Client(timeout=30) as client:
        response = client.post(
            SARVAM_STT_URL,
            headers={"api-subscription-key": SARVAM_API_KEY},
            files={"file": (filename, audio_bytes, "audio/wav")},
            data={"model": "saarika:v2.5", "language_code": "en-IN"},
        )
        response.raise_for_status()
        return response.json().get("transcript", "")


def synthesize(text: str, language: str = "en-IN") -> bytes:
    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(
                SARVAM_TTS_URL,
                headers={
                    "api-subscription-key": SARVAM_API_KEY,
                    "Content-Type": "application/json",
                },
                json={
                    "inputs": [text],
                    "target_language_code": language,
                    "speaker": "anushka",
                    "pitch": 0,
                    "pace": 1.0,
                    "loudness": 1.5,
                    "speech_sample_rate": 22050,
                    "enable_preprocessing": True,
                    "model": "bulbul:v2",
                },
            )
            response.raise_for_status()
            audio_b64 = response.json()["audios"][0]
            return base64.b64decode(audio_b64)
    except Exception as e:
        print(f"[!] Sarvam TTS failed ({e}), falling back to macOS say")
        return _say_fallback(text)


def _say_fallback(text: str) -> bytes:
    aiff_fd, aiff_path = tempfile.mkstemp(suffix=".aiff")
    wav_fd, wav_path = tempfile.mkstemp(suffix=".wav")
    os.close(aiff_fd)
    os.close(wav_fd)
    try:
        subprocess.run(["say", "-o", aiff_path, text], check=True, capture_output=True)
        subprocess.run(
            ["afconvert", aiff_path, wav_path, "-d", "LEI16", "-f", "WAVE"],
            check=True,
            capture_output=True,
        )
        with open(wav_path, "rb") as f:
            return f.read()
    finally:
        for p in [aiff_path, wav_path]:
            try:
                os.unlink(p)
            except FileNotFoundError:
                pass
