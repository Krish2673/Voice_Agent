import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ASSEMBLYAI_API_KEY = os.getenv("AssemblyAI_API_KEY")
GEMINI_API_KEY = os.getenv("Gemini_API_KEY")
MURF_API_KEY = os.getenv("MURF_API_KEY")

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
