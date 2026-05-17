"""
Continuous mic listener with VAD.
Say "Hey Dev" to wake, then give a command.
Runs against the local /voice endpoint.
"""

import io
import os
import sys
import time
import tempfile
import wave
import subprocess
from collections import deque
from urllib.parse import unquote

import httpx
import sounddevice as sd
import webrtcvad

SERVER_URL        = "http://localhost:8000/voice"
MUSIC_STATUS_URL  = "http://localhost:8000/api/music-playing"
_suppress_until: float = 0.0   # mic suppressed until this timestamp
SAMPLE_RATE = 16000
FRAME_MS = 30
FRAME_SAMPLES = int(SAMPLE_RATE * FRAME_MS / 1000)   # 480 samples
VAD_AGGRESSIVENESS = 2
SILENCE_FRAMES = int(1000 / FRAME_MS)                 # 1 s silence → end recording
MIN_SPEECH_FRAMES = int(500 / FRAME_MS)               # discard clips < 500 ms
PRE_ROLL_FRAMES = 10                                  # 300 ms before speech onset
MAX_SPEECH_FRAMES = int(30_000 / FRAME_MS)            # hard cap at 30 s


# ── Volume helpers (for music ducking) ────────────────────────────────────────

def _is_music_playing() -> bool:
    try:
        r = httpx.get(MUSIC_STATUS_URL, timeout=0.5)
        return r.json().get("playing", False)
    except Exception:
        return False

def _get_volume() -> int:
    r = subprocess.run(
        ['osascript', '-e', 'output volume of (get volume settings)'],
        capture_output=True, text=True
    )
    try:
        return int(r.stdout.strip())
    except Exception:
        return 70

def _set_volume(level: int):
    subprocess.run(
        ['osascript', '-e', f'set volume output volume {level}'],
        capture_output=True
    )

# ── Audio helpers ──────────────────────────────────────────────────────────────

def _to_wav(frames: list[bytes]) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(b"".join(frames))
    return buf.getvalue()


def _play_wav(wav_bytes: bytes):
    """Play WAV bytes using macOS afplay. Suppresses mic during + 1.5s after to prevent echo."""
    global _suppress_until
    fd, path = tempfile.mkstemp(suffix=".wav")
    try:
        os.write(fd, wav_bytes)
        os.close(fd)
        _suppress_until = time.time() + 9999   # mute mic while playing
        subprocess.run(["afplay", path], check=True)
    except Exception as e:
        print(f"[!] Playback error: {e}")
    finally:
        _suppress_until = time.time() + 2.5    # 2.5s cooldown after playback ends
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass


# ── Server communication ───────────────────────────────────────────────────────

def _send(wav_bytes: bytes) -> dict:
    for attempt in range(3):
        try:
            resp = httpx.post(
                SERVER_URL,
                files={"audio": ("recording.wav", wav_bytes, "audio/wav")},
                timeout=60,
            )
            print(f"[←] Server: {resp.status_code}  content-type: {resp.headers.get('content-type','?')}")
            if "audio/wav" in resp.headers.get("content-type", ""):
                return {
                    "audio": resp.content,
                    "transcript": unquote(resp.headers.get("x-transcript", "")),
                    "intent": resp.headers.get("x-intent", "{}"),
                    "action_result": resp.headers.get("x-action-result", "{}"),
                }
            if "application/json" in resp.headers.get("content-type", ""):
                return resp.json()
            # Server error with non-JSON body — ignore silently
            print(f"[!] Server returned {resp.status_code}, skipping")
            return {"ignored": True}
        except httpx.ConnectError:
            if attempt < 2:
                wait = 2 ** attempt
                print(f"[!] Server unreachable, retrying in {wait}s ({attempt+1}/3)…")
                time.sleep(wait)
            else:
                print("[!] Server unreachable after 3 attempts. Exiting.")
                sys.exit(1)
    return {}


# ── VAD recording loop ─────────────────────────────────────────────────────────

def _record_utterance() -> bytes:
    vad = webrtcvad.Vad(VAD_AGGRESSIVENESS)
    ring = deque(maxlen=PRE_ROLL_FRAMES)
    recording = False
    recorded: list[bytes] = []
    silent = 0
    speech = 0

    try:
        stream = sd.RawInputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16",
            blocksize=FRAME_SAMPLES,
        )
    except Exception as e:
        print(f"[!] Microphone error: {e}")
        print("[!] Check mic permissions: System Settings → Privacy → Microphone")
        sys.exit(1)

    with stream:
        while True:
            raw, _ = stream.read(FRAME_SAMPLES)
            frame = bytes(raw)

            # Discard frames while speaker is playing or in cooldown
            if time.time() < _suppress_until:
                ring.clear()
                continue

            try:
                is_speech = vad.is_speech(frame, SAMPLE_RATE)
            except Exception:
                is_speech = False

            if not recording:
                ring.append(frame)
                if is_speech:
                    recording = True
                    recorded = list(ring)
                    silent = 0
                    speech = 1
                    print("[*] Speech detected…", end=" ", flush=True)
            else:
                recorded.append(frame)
                if is_speech:
                    speech += 1
                    silent = 0
                else:
                    silent += 1

                if silent >= SILENCE_FRAMES or speech >= MAX_SPEECH_FRAMES:
                    if speech >= MIN_SPEECH_FRAMES:
                        print(f"done ({speech * FRAME_MS}ms of speech)")
                        return _to_wav(recorded)
                    # too short, reset
                    recording = False
                    recorded = []
                    silent = 0
                    speech = 0
                    ring.clear()
                    print("(too short, ignored)")


# ── Main loop ─────────────────────────────────────────────────────────────────

def main():
    print("=== Voice Home Control ===")
    print("Say 'Hey Dev' to activate\n")

    try:
        sd.query_devices(kind="input")
    except Exception as e:
        print(f"[!] No input device found: {e}")
        print("[!] Check mic permissions: System Settings → Privacy → Microphone")
        sys.exit(1)

    while True:
        try:
            print("[…] Listening…")

            # Duck music while recording so VAD isn't confused by speaker noise
            saved_vol = None
            if _is_music_playing():
                saved_vol = _get_volume()
                _set_volume(15)
                print("[♫] Music ducked for listening…")

            wav = _record_utterance()

            if saved_vol is not None:
                _set_volume(90)  # restore to music volume after ducking

            print("[→] Sending to server…")
            result = _send(wav)

            if result.get("ignored"):
                t = result.get("transcript", "")
                err = result.get("error", "")
                print(f"[~] Ignored — heard: {t!r}  {('err: ' + err) if err else ''}\n")
                continue

            print(f"[T] Transcript  : {result.get('transcript', '')}")
            print(f"[I] Intent      : {result.get('intent', '')}")
            print(f"[R] Result      : {result.get('action_result', '')}")

            audio = result.get("audio")
            if audio:
                print(f"[♪] Playing response ({len(audio)} bytes)…")
                _play_wav(audio)
            else:
                print("[!] No audio in response")

            print()

        except KeyboardInterrupt:
            print("\n[✓] Stopped.")
            break
        except Exception as e:
            print(f"[!] Error: {e}\n")
            continue


if __name__ == "__main__":
    main()
