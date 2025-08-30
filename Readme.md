# 🤖 Glitzo – The Conversational Voice Agent

A real-time voice conversational AI built with FastAPI, WebSockets, AssemblyAI (STT), Google Gemini (LLM), Murf.ai (TTS), and a modern frontend.
Glitzo listens to your voice, understands it, responds with wit and humor, and speaks back — all in real-time streaming.

It’s like talking to a geeky dev friend who also cracks coding jokes while helping you out. 🐞💻

---

## 🚀 Features

- **🎤 Real-Time Voice Input** – Stream your microphone audio directly to the backend.
- **📝 Live Speech-to-Text (STT)** – Powered by AssemblyAI streaming API, with partial + final transcripts.
- **🧠 Smart Conversation** – Responses generated via Gemini 2.0 Flash with a fun dev-persona ("Glitzo").
- **🔊 Instant Text-to-Speech (TTS)** – Streams back natural speech via Murf.ai.
- **⚡ Streaming Chat UI** – Messages and audio arrive chunk-by-chunk, no waiting for full responses.
- **📰 Tech News Mode** – If you ask for "latest tech news", Glitzo fetches real headlines from HackerNews API, summarizes them with Gemini, and reads them aloud.
- **🔑 API Key Config in UI** – Users can enter their own Gemini, Murf, and AssemblyAI API keys in a settings modal (stored locally).
- **💬 Persistent Chat History** – Maintains session-based conversations.
- **🎨 Modern UI** – Clean frontend with smooth streaming playback and recording controls.
- **⚠️ Error Handling** – Informs user if keys are missing, mic issues, or API errors occur.

---

## 🛠️ Technologies Used

**Frontend**
- HTML5, CSS3, Vanilla JS
- Web Audio API + WebSockets
- LocalStorage for API keys

**Backend**
- Python 3.11+
- FastAPI (WebSocket server + API routes)
- AssemblyAI SDK (real-time STT)
- Google Gemini via google.genai (LLM)
- Murf.ai (streaming TTS)
- httpx (async API calls)

**Others**
- HackerNews API (for tech news)
- Render.com (deployment)

---

## 🏗️ Architecture

User Speaks (Mic)  
    ⬇  
Frontend (JS) — captures audio —> FastAPI Backend  
        ⬇  
AssemblyAI (Speech-to-Text) → Gemini LLM (Generate Reply) → Murf.ai (TTS)  
        ⬇  
Backend sends audio URL + reply text  
        ⬇  
Frontend displays chat bubbles + plays reply audio


---

## 📂 Project Structure

```bash
Murf_AI_Agent/
├── frontend/
│   ├── index.html        # UI layout
│   ├── style.css         # Styles
│   └── script.js         # Frontend logic
├── backend/
│   ├── main.py           # FastAPI Backend
│   ├── routes/           # API route handlers
│   │   ├── ws.py      # WebSocket streaming (STT + LLM + TTS)
│   │   └── news.py       # HackerNews tech news fetcher
│   ├── utils/            # Helper functions
│   │   ├── logger.py        # Logger Setup
├── requirements.txt      # Python dependencies
└── README.md             # Documentation
```

---

## ▶️ How to Run Locally


### 1️⃣ Clone the repository
```bash
git clone https://github.com/Krish2673/Voice_Agent.git

cd voice-bot
```

### 2️⃣ Install dependencies
```bash
pip install -r requirements.txt
```

### 3️⃣ Start Backend server
```bash
uvicorn backend.main:app --reload
```

### 4️⃣ Open in browser

Navigate to http://127.0.0.1:8000 in your browser.

## 🔑 API Keys Setup

Unlike traditional `.env` files, Glitzo allows you to **enter your API keys directly in the UI**:

1. Click **⚙️ Settings** in the app.  
2. Enter your keys:  
   - **Gemini API Key**  
   - **Murf API Key**  
   - **AssemblyAI API Key**  
3. Keys are stored in your browser (**LocalStorage**).

---

## 🌍 Deployment

The agent is live on **Render.com** 🚀  
👉 [Glitzo.com](https://glitzo.onrender.com)
