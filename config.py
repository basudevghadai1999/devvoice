from dotenv import load_dotenv
import os

load_dotenv()

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")

DEVICES = {
    "plug": {
        "dev_id": os.getenv("TUYA_DEVICE_ID"),
        "address": os.getenv("TUYA_ADDRESS"),
        "local_key": os.getenv("TUYA_LOCAL_KEY"),
        "version": float(os.getenv("TUYA_VERSION", "3.5")),
    }
}

WAKE_PHRASES = [
    "hi there", "hello there", "hey there",
    "hi dear", "hello dear", "high there",   # Sarvam mishearings
    "hi dev", "hey dev", "hello dev",         # fallback
]
WAKE_TIMEOUT_SECONDS = 30
