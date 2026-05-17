import json
import re
import time
import asyncio
import threading
from urllib.parse import quote
from fastapi import FastAPI, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from services import sarvam, gemma_intent, tuya_control, search, calendar_service, notes_service, music_service
from config import WAKE_PHRASES, WAKE_TIMEOUT_SECONDS

app = FastAPI(title="Voice Home Control")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── WebSocket state manager ────────────────────────────────────────────────────

class StateManager:
    def __init__(self):
        self.connections: list[WebSocket] = []
        self.state = "idle"

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.append(ws)
        await ws.send_text(json.dumps({"state": self.state}))

    def disconnect(self, ws: WebSocket):
        if ws in self.connections:
            self.connections.remove(ws)

    async def broadcast(self, state: str, **extra):
        self.state = state
        msg = json.dumps({"state": state, **extra})
        dead = []
        for ws in self.connections:
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.connections.remove(ws)

state_mgr = StateManager()

@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await state_mgr.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        state_mgr.disconnect(websocket)

# ── Wake state ─────────────────────────────────────────────────────────────────

_wake_lock = threading.Lock()
_wake_expires_at: float = 0.0

def _is_wake_active() -> bool:
    with _wake_lock:
        return time.time() < _wake_expires_at

def _set_wake(active: bool):
    global _wake_expires_at
    with _wake_lock:
        _wake_expires_at = time.time() + WAKE_TIMEOUT_SECONDS if active else 0.0

# ── Helpers ────────────────────────────────────────────────────────────────────

def _clean(text: str) -> str:
    return re.sub(r"[^\w\s]", "", text.lower()).strip()

def _detect_wake(text: str) -> tuple[bool, str]:
    clean = _clean(text)
    for phrase in WAKE_PHRASES:
        if clean.startswith(phrase):
            return True, clean[len(phrase):].strip()
        if phrase in clean:
            return True, clean[clean.index(phrase) + len(phrase):].strip()
    return False, ""

def _detect_language(text: str) -> str:
    if any("ऀ" <= ch <= "ॿ" for ch in text):
        return "hi-IN"
    if any(m in text.lower() for m in ["karo", "band", "chalu", "plug ko"]):
        return "hi-IN"
    return "en-IN"

def _confirmation(result: dict, language: str) -> str:
    action = result.get("action", "status")
    device = result.get("device", "device")
    if language == "hi-IN":
        if action == "on":  return f"{device} चालू कर दिया"
        if action == "off": return f"{device} बंद कर दिया"
        on = result.get("on", False)
        return f"{device} {'चालू' if on else 'बंद'} है"
    else:
        if action == "on":  return f"{device} is now on"
        if action == "off": return f"{device} is now off"
        on = result.get("on", False)
        v, p = result.get("voltage_v", 0), result.get("power_w", 0)
        return f"{device} is {'on' if on else 'off'}, {v} V, {p} W"

def _audio_response(audio: bytes, transcript: str, intent: dict, result: dict) -> Response:
    return Response(
        content=audio,
        media_type="audio/wav",
        headers={
            "X-Transcript":    quote(transcript, safe=" "),
            "X-Intent":        json.dumps(intent, ensure_ascii=True),
            "X-Action-Result": json.dumps(result, ensure_ascii=True),
        },
    )

async def _idle_after(seconds: float):
    await asyncio.sleep(seconds)
    await state_mgr.broadcast("idle", transcript="", response="")

# ── Voice endpoint ─────────────────────────────────────────────────────────────

@app.post("/voice")
async def voice_command(audio: UploadFile = File(...)):
    audio_bytes = await audio.read()
    loop = asyncio.get_event_loop()

    await state_mgr.broadcast("processing")

    try:
        transcript = await loop.run_in_executor(None,
            lambda: sarvam.transcribe(audio_bytes, audio.filename or "audio.wav"))
    except Exception as e:
        print(f"  STT error: {e}")
        await state_mgr.broadcast("idle")
        return JSONResponse({"ignored": True, "transcript": "", "error": str(e)})

    if not transcript:
        await state_mgr.broadcast("idle")
        return JSONResponse({"ignored": True, "transcript": "", "error": "empty transcript"})

    wake_found, remainder = _detect_wake(transcript)
    language = _detect_language(transcript)

    # Keep wake alive while music is playing so user can say "stop"/"next" without wake phrase
    music_active = (music_service._music_proc is not None and
                    music_service._music_proc.poll() is None)
    if music_active:
        _set_wake(True)

    print(f"  transcript : {transcript!r}")
    print(f"  wake={wake_found}  remainder={remainder!r}  lang={language}  active={_is_wake_active()}  music={music_active}")

    if not wake_found and not _is_wake_active():
        await state_mgr.broadcast("idle")
        return JSONResponse({"ignored": True, "transcript": transcript})

    # Case a — wake only
    if wake_found and not remainder:
        _set_wake(True)
        await state_mgr.broadcast("listening", transcript=transcript, response="")
        ack = "हाँ, मैं सुन रहा हूँ" if language == "hi-IN" else "Yes, how can I help?"
        audio_out = await loop.run_in_executor(None, lambda: sarvam.synthesize(ack, language))
        await state_mgr.broadcast("speaking", transcript=transcript, response=ack)
        asyncio.create_task(_idle_after(len(audio_out) / 44100 + 2))
        return _audio_response(audio_out, transcript, {"wake": True}, {"acknowledged": True})

    # Cases b & c — command
    command = remainder if (wake_found and remainder) else transcript
    _set_wake(True)

    await state_mgr.broadcast("thinking", transcript=transcript, response="")
    try:
        intent = await loop.run_in_executor(None, lambda: gemma_intent.parse_intent(command))
    except Exception as e:
        print(f"  Intent parse error: {e}")
        intent = {"type": "unknown", "confidence": 0.0}
    print(f"  intent : {intent}")
    intent_type = intent.get("type", "unknown")

    if intent_type == "query":
        question = intent.get("question", command)
        answer_text = await loop.run_in_executor(None, lambda: search.answer(question))
        audio_out = await loop.run_in_executor(None, lambda: sarvam.synthesize(answer_text, language))
        await state_mgr.broadcast("speaking", transcript=transcript, response=answer_text)
        asyncio.create_task(_idle_after(len(audio_out) / 44100 + 2))
        return _audio_response(audio_out, transcript, intent, {"answer": answer_text})

    if intent_type == "reminder":
        if not calendar_service.is_configured():
            msg = "Google Calendar is not set up. Please run python setup_google_calendar.py first."
        else:
            try:
                msg = await loop.run_in_executor(None, lambda: calendar_service.add_event(
                    title            = intent.get("title", "Reminder"),
                    when_iso         = intent.get("when", ""),
                    duration_minutes = int(intent.get("duration_minutes", 60)),
                    description      = intent.get("description", ""),
                ))
            except Exception as e:
                print(f"  Calendar error: {e}")
                msg = "Sorry, I couldn't add that to your calendar."
        audio_out = await loop.run_in_executor(None, lambda: sarvam.synthesize(msg, language))
        await state_mgr.broadcast("speaking", transcript=transcript, response=msg)
        asyncio.create_task(_idle_after(len(audio_out) / 44100 + 2))
        return _audio_response(audio_out, transcript, intent, {"reminder": msg})

    if intent_type == "calendar_list":
        if not calendar_service.is_configured():
            msg = "Google Calendar is not set up. Please run python setup_google_calendar.py first."
        else:
            try:
                timeframe = intent.get("timeframe", "today")
                msg = await loop.run_in_executor(None, lambda: calendar_service.list_events(timeframe))
            except Exception as e:
                print(f"  Calendar error: {e}")
                msg = "Sorry, I couldn't fetch your calendar."
        audio_out = await loop.run_in_executor(None, lambda: sarvam.synthesize(msg, language))
        await state_mgr.broadcast("speaking", transcript=transcript, response=msg)
        asyncio.create_task(_idle_after(len(audio_out) / 44100 + 2))
        return _audio_response(audio_out, transcript, intent, {"calendar": msg})

    if intent_type == "note_add":
        content = intent.get("content", command)
        msg = await loop.run_in_executor(None, lambda: notes_service.add_note(content))
        audio_out = await loop.run_in_executor(None, lambda: sarvam.synthesize(msg, language))
        await state_mgr.broadcast("speaking", transcript=transcript, response=msg)
        asyncio.create_task(_idle_after(len(audio_out) / 44100 + 2))
        return _audio_response(audio_out, transcript, intent, {"note": msg})

    if intent_type == "note_read":
        query = intent.get("query", "")
        msg = await loop.run_in_executor(None, lambda: notes_service.search_notes(query))
        audio_out = await loop.run_in_executor(None, lambda: sarvam.synthesize(msg, language))
        await state_mgr.broadcast("speaking", transcript=transcript, response=msg)
        asyncio.create_task(_idle_after(len(audio_out) / 44100 + 2))
        return _audio_response(audio_out, transcript, intent, {"notes": msg})

    if intent_type == "music":
        action = intent.get("action", "play_pause")
        if action == "play_song":
            query = intent.get("query", command)
            await state_mgr.broadcast("thinking", transcript=transcript, response="Searching for music...")
            msg = await loop.run_in_executor(None, lambda: music_service.play_song(query))
        elif action == "next":
            msg = await loop.run_in_executor(None, music_service.next_track)
        elif action == "previous":
            msg = await loop.run_in_executor(None, music_service.previous_track)
        elif action == "stop":
            msg = await loop.run_in_executor(None, music_service.stop_music)
        elif action == "volume_up":
            msg = await loop.run_in_executor(None, music_service.volume_up)
        elif action == "volume_down":
            msg = await loop.run_in_executor(None, music_service.volume_down)
        elif action == "volume":
            level = int(intent.get("level", 50))
            msg = await loop.run_in_executor(None, lambda: music_service.set_volume(level))
        else:
            msg = await loop.run_in_executor(None, music_service.play_pause)
        audio_out = await loop.run_in_executor(None, lambda: sarvam.synthesize(msg, language))
        await state_mgr.broadcast("speaking", transcript=transcript, response=msg)
        asyncio.create_task(_idle_after(len(audio_out) / 44100 + 2))
        return _audio_response(audio_out, transcript, intent, {"music": msg})

    if intent_type == "control" and intent.get("confidence", 0) >= 0.5:
        try:
            result = await loop.run_in_executor(None, lambda: tuya_control.execute(intent))
        except Exception as e:
            print(f"  Tuya error: {e}")
            result = {"error": str(e)}
        confirmation = _confirmation(result, language) if "error" not in result else (
            "डिवाइस से कनेक्ट नहीं हो पाया" if language == "hi-IN" else "Could not connect to device"
        )
        audio_out = await loop.run_in_executor(None, lambda: sarvam.synthesize(confirmation, language))
        await state_mgr.broadcast("speaking", transcript=transcript, response=confirmation)
        asyncio.create_task(_idle_after(len(audio_out) / 44100 + 2))
        return _audio_response(audio_out, transcript, intent, result)

    if intent_type == "chat":
        reply = intent.get("reply", "Sure!")
        audio_out = await loop.run_in_executor(None, lambda: sarvam.synthesize(reply, language))
        await state_mgr.broadcast("speaking", transcript=transcript, response=reply)
        asyncio.create_task(_idle_after(len(audio_out) / 44100 + 2))
        return _audio_response(audio_out, transcript, intent, {"reply": reply})

    sorry = "माफ़ कीजिए, समझ नहीं आया" if language == "hi-IN" else "Sorry, I didn't understand that"
    audio_out = await loop.run_in_executor(None, lambda: sarvam.synthesize(sorry, language))
    await state_mgr.broadcast("speaking", transcript=transcript, response=sorry)
    asyncio.create_task(_idle_after(len(audio_out) / 44100 + 2))
    return _audio_response(audio_out, transcript, intent, {"error": "unknown intent"})

# ── Other endpoints ────────────────────────────────────────────────────────────

@app.get("/status")
def device_status(device: str = "plug"):
    return tuya_control.get_status(device)

@app.get("/api/state")
def get_state():
    return {"state": state_mgr.state}

@app.get("/api/music-playing")
def music_playing_status():
    proc = music_service._music_proc
    return {"playing": proc is not None and proc.poll() is None}

@app.get("/")
def root():
    return {"status": "ok", "endpoints": ["/voice (POST)", "/ws (WS)", "/status (GET)"]}
