# 🎙️ Conversational Voice Bot

A fully functional **voice-based conversational agent** built with **FastAPI**, **JavaScript**, **AssemblyAI**, **Google Gemini LLM**, and **Murf.ai TTS**.  
The bot listens to your voice, transcribes it, sends the text to an AI model for a reply, and speaks back the response — creating a real-time two-way conversation.

---

## 🚀 Features

- **🎤 Voice Input:** Record and send voice directly from the browser.
- **📝 Speech-to-Text:** Uses **AssemblyAI** to transcribe audio into text.
- **🧠 AI Conversation:** Powered by **Google Gemini** for intelligent replies.
- **🔊 Text-to-Speech:** Converts AI responses into audio using **Murf.ai**.
- **💬 Chat History:** Maintains conversation state for each session.
- **🎨 Modern UI:** Responsive and styled with smooth animations.
- **⚠️ Error Handling:** Gracefully handles errors and informs the user.

---

## 🛠️ Technologies Used

**Frontend**
- HTML5, CSS3, JavaScript
- MediaRecorder API (for audio capture)

**Backend**
- Python 3.10+
- FastAPI
- AssemblyAI SDK
- Google Gemini (via `google.genai`)
- Murf.ai Python SDK

**Others**
- Environment variables for API keys
- Session-based conversation tracking

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
Frontend plays reply audio + updates chat history


---

## 📂 Project Structure

.<br>
├── frontend/<br>
│ ├── index.html # UI layout<br>
│ ├── style.css # Styles<br>
│ └── script.js # Frontend logic<br>
├── backend/<br>
│ ├── main.py # FastAPI backend<br>
├── requirements.txt # Python dependencies<br>
└── README.md

---

## ⚙️ Environment Variables

Create a `.env` file in the project root with:

AssemblyAI_API_KEY = your_assemblyai_api_key<br>
Gemini_API_KEY = your_google_gemini_api_key<br>
MURF_API_KEY = your_murf_ai_api_key<br>

---

## ▶️ How to Run


### 1️⃣ Clone the repository
```bash
git clone https://github.com/Krish2673/Voice_Agent.git

cd voice-bot
```

### 2️⃣ Install dependencies
```bash
pip install -r requirements.txt
```

### 3️⃣ Add environment variables

Create a .env file with the keys shown above.

### 4️⃣ Start the server
```bash
uvicorn backend.main:app --reload
```

### 5️⃣ Open in browser

Go to:
http://127.0.0.1:8000