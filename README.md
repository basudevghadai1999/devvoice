# 🎙️ Voice Home Control — "Dev"

A fully local, voice-controlled smart home assistant that runs on macOS. Speak commands in **English or Hindi** to control IoT devices, play music, set reminders, take notes, search the web, and have casual conversations — all powered by **Ollama (Gemma 4 26B)** running locally on your machine.

---

## 🎬 Demo

https://github.com/basudevghadai1999/ai_voice_assistant/blob/main/voice_video.mp4

---

## 📌 What This Project Does

**Dev** is a personal voice assistant that:

| Feature | How It Works |
|---|---|
| 🔌 **Smart Plug Control** | Turn on/off Tuya smart plugs via local network (no cloud) |
| 🎵 **Music Playback** | Play any song from YouTube via `yt-dlp`, control Spotify/Apple Music |
| 📅 **Calendar & Reminders** | Add events and check your schedule via Google Calendar API |
| 📝 **Notes** | Save and search voice notes (stored locally as JSON) |
| 🔍 **Web Search** | Answer real-time questions using DuckDuckGo + LLM summarization |
| 🌤️ **Weather** | Fetch live weather from wttr.in |
| 💬 **Chat** | Casual conversation with personality |
| 🗣️ **Bilingual** | Understands and responds in English and Hindi |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React + Vite)               │
│              http://localhost:3000                        │
│  ┌───────────┐  ┌───────────┐  ┌──────────────────────┐ │
│  │ VoiceOrb  │  │ State     │  │ WebSocket (live       │ │
│  │ Animation │  │ Labels    │  │ state updates)        │ │
│  └───────────┘  └───────────┘  └──────────────────────┘ │
└──────────────────────┬──────────────────────────────────┘
                       │ proxy → :8000
┌──────────────────────▼──────────────────────────────────┐
│                Backend (FastAPI + Uvicorn)                │
│              http://localhost:8000                        │
│                                                          │
│  POST /voice ──► STT (Sarvam) ──► Intent (Gemma 4 26B)  │
│                       │                  │               │
│                       ▼                  ▼               │
│              ┌────────────────────────────────────┐      │
│              │  Action Router                     │      │
│              │  ├─ control  → Tuya smart plug     │      │
│              │  ├─ music    → yt-dlp / Spotify    │      │
│              │  ├─ reminder → Google Calendar      │      │
│              │  ├─ note     → Local JSON storage   │      │
│              │  ├─ query    → DuckDuckGo + Gemma   │      │
│              │  ├─ chat     → Gemma conversational  │      │
│              │  └─ weather  → wttr.in API          │      │
│              └────────────────────────────────────┘      │
│                       │                                  │
│                       ▼                                  │
│              TTS (Sarvam) ──► Audio response to client   │
└──────────────────────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│            Voice Client (Python CLI)                     │
│  Continuous mic listener with VAD (Voice Activity        │
│  Detection). Records speech → sends to /voice →          │
│  plays audio response via macOS afplay                   │
└──────────────────────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│              Ollama (Local LLM)                          │
│              http://localhost:11434                       │
│              Model: gemma4:26b (Q4_K_M, ~17GB)           │
└──────────────────────────────────────────────────────────┘
```

---

## 📂 Project Structure

```
voice-home-control/
├── server.py                  # FastAPI backend — main entry point
├── voice_client.py            # CLI mic listener with VAD
├── config.py                  # Environment config loader
├── setup_google_calendar.py   # One-time Google Calendar OAuth setup
├── .env.example               # Environment template (copy to .env)
├── requirements.txt           # Python dependencies
├── voice_video.mp4            # Demo video
│
├── services/
│   ├── gemma_intent.py        # Intent classification via Ollama (Gemma 4)
│   ├── search.py              # Web search + Q&A via Ollama
│   ├── sarvam.py              # Speech-to-Text & Text-to-Speech (Sarvam AI)
│   ├── tuya_control.py        # Tuya smart plug control (local network)
│   ├── calendar_service.py    # Google Calendar integration
│   ├── notes_service.py       # Local JSON-based notes
│   └── music_service.py       # YouTube/Spotify/Apple Music playback
│
├── frontend/                  # React + Vite web dashboard
│   ├── package.json
│   ├── vite.config.js         # Dev server with proxy to backend
│   └── src/
│       ├── main.jsx
│       ├── App.jsx            # Main app with WebSocket state
│       ├── App.css            # Full styling with animations
│       └── components/
│           └── VoiceOrb.jsx   # Animated voice state indicator
│
└── .gitignore                 # Excludes .env, tokens, node_modules
```

---

## 🔧 Prerequisites

| Requirement | Install Command |
|---|---|
| **Python 3.10+** | `brew install python` |
| **Node.js 18+** | `brew install node` |
| **Ollama** | `brew install ollama` |
| **Gemma 4 26B model** | `ollama pull gemma4:26b` |
| **yt-dlp** (for music) | `brew install yt-dlp` |
| **Sarvam AI API key** | Sign up at [sarvam.ai](https://www.sarvam.ai/) |
| **Tuya smart plug** (optional) | Need device ID, local key, and IP address |

---

## 🚀 Setup & Run

### Step 1 — Clone & Install Dependencies

```bash
# Clone the repository
git clone https://github.com/basudevghadai/voice-home-control.git
cd voice-home-control

# Install Python dependencies
pip3 install -r requirements.txt

# Install frontend dependencies
cd frontend
npm install
cd ..
```

### Step 2 — Configure Environment

```bash
# Copy the example env file
cp .env.example .env
```

Edit `.env` with your actual values:

```env
# Sarvam AI (Speech-to-Text & Text-to-Speech)
SARVAM_API_KEY=your_sarvam_api_key_here

# Ollama (Local LLM)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma4:26b

# Tuya Smart Plug (optional — skip if you don't have one)
TUYA_DEVICE_ID=your_device_id
TUYA_ADDRESS=192.168.1.x
TUYA_LOCAL_KEY=your_local_key
TUYA_VERSION=3.5
```

### Step 3 — Start Ollama

Make sure Ollama is running and the model is loaded:

```bash
# Start Ollama service (if not already running)
ollama serve

# In another terminal, pull the model (first time only)
ollama pull gemma4:26b

# Verify it's available
ollama list
```

### Step 4 — (Optional) Set Up Google Calendar

If you want calendar/reminder features:

```bash
# 1. Go to https://console.cloud.google.com/
# 2. Create a project → Enable "Google Calendar API"
# 3. Create OAuth credentials (Desktop app)
# 4. Download as credentials.json into the project root

python3 setup_google_calendar.py
# This opens a browser for OAuth — authorize and token.json is saved
```

### Step 5 — Start the Backend

```bash
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

You should see:

```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Started reloader process
```

### Step 6 — Start the Frontend

Open a **new terminal**:

```bash
cd frontend
npm run dev
```

You should see:

```
  VITE v5.4.x  ready in XXX ms

  ➜  Local:   http://localhost:3000/
  ➜  Network: http://192.168.x.x:3000/
```

Open **http://localhost:3000** in your browser to see the voice assistant dashboard with the animated orb.

### Step 7 — Start the Voice Client

Open another **new terminal**:

```bash
python3 voice_client.py
```

You should see:

```
=== Voice Home Control ===
Say 'Hey Dev' to activate

[…] Listening…
```

> **Note:** On first run, macOS will ask for microphone permission. Grant it in **System Settings → Privacy & Security → Microphone**.

---

## 🎯 How to Use

### Wake Word

Say **"Hi there"**, **"Hey there"**, or **"Hi Dev"** to activate the assistant. Then give your command.

### Example Commands

| What You Say | What Happens |
|---|---|
| *"Hi there"* | Activates and says "Yes, how can I help?" |
| *"Turn on the plug"* | Turns on your Tuya smart plug |
| *"Plug band karo"* (Hindi) | Turns off the plug |
| *"What's the weather in Mumbai?"* | Fetches live weather |
| *"Play Shape of You"* | Downloads & plays the song from YouTube |
| *"Next song"* / *"Agla gana"* | Skips to next track |
| *"Stop the music"* / *"Gana band karo"* | Stops playback |
| *"Volume up"* / *"Awaaz badao"* | Increases system volume |
| *"Remind me to call mom at 3pm"* | Creates a Google Calendar event |
| *"What's on my calendar today?"* | Lists today's events |
| *"Add a note: buy milk and eggs"* | Saves a note locally |
| *"What are my notes?"* | Reads back recent notes |
| *"Who is the PM of India?"* | Answers using LLM knowledge |
| *"Thank you"* | Responds with a friendly reply |

---

## 🔄 Full Request Flow

```
1. 🎤 User speaks into microphone
2. 🔊 Voice Client detects speech (VAD) and records audio
3. 📡 Audio is sent to POST /voice on the backend
4. 🗣️ Sarvam AI transcribes audio → text
5. 🔍 Wake word detection ("Hi there" / "Hey Dev")
6. 🧠 Gemma 4 (via Ollama) classifies intent → JSON
7. ⚡ Action router executes the command:
   - Smart plug → Tuya local API
   - Music → yt-dlp download + afplay
   - Calendar → Google Calendar API
   - Notes → Local JSON file
   - Search → DuckDuckGo + Gemma summarization
   - Weather → wttr.in API
   - Chat → Gemma generates reply
8. 🔈 Sarvam AI converts response text → speech audio
9. 📨 Audio WAV sent back to voice client
10. 🔊 Voice client plays audio via macOS afplay
11. 📊 Frontend dashboard updates in real-time via WebSocket
```

---

## 🖥️ Running Summary

You need **3–4 terminals** running simultaneously:

| Terminal | Command | Port |
|---|---|---|
| **1. Ollama** | `ollama serve` | `:11434` |
| **2. Backend** | `uvicorn server:app --reload --host 0.0.0.0 --port 8000` | `:8000` |
| **3. Frontend** | `cd frontend && npm run dev` | `:3000` |
| **4. Voice Client** | `python3 voice_client.py` | — |

> Ollama may already be running as a background service — check with `ollama list`.

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| **LLM** | Gemma 4 26B via Ollama (local, private) |
| **Speech-to-Text** | Sarvam AI (saarika:v2.5) |
| **Text-to-Speech** | Sarvam AI (bulbul:v2) |
| **Backend** | Python, FastAPI, Uvicorn |
| **Frontend** | React 18, Vite 5 |
| **Smart Home** | TinyTuya (local LAN control) |
| **Music** | yt-dlp, afplay, Spotify/Apple Music |
| **Calendar** | Google Calendar API |
| **Web Search** | DuckDuckGo Search |
| **Weather** | wttr.in |
| **Voice Detection** | WebRTC VAD |

---

## ⚠️ Troubleshooting

| Problem | Solution |
|---|---|
| `python: command not found` | Use `python3` instead — macOS doesn't alias `python` by default |
| Microphone not working | Grant permission: **System Settings → Privacy → Microphone** |
| Ollama connection refused | Run `ollama serve` or check if it's running with `ollama list` |
| Slow LLM responses | Gemma 4 26B is large (~17GB). Use `gemma3:4b` for faster inference by editing `.env` |
| yt-dlp not found | Install with `brew install yt-dlp` |
| Google Calendar errors | Run `python3 setup_google_calendar.py` to re-authorize |
| Tuya device unreachable | Ensure the device is on the same LAN and the local key is correct |
| Frontend can't connect | Make sure the backend is running on port 8000 |

---

## 📄 License

This project is for personal/educational use.

---

**Built by Basudev** 🚀
