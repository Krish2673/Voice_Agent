from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from murf import Murf
from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/", response_class=HTMLResponse)
async def get_index():
    with open("frontend/index.html", "r") as f:
        return f.read()

class TTSRequest(BaseModel):
    text: str
    voice_id: str = "en-US-terrell" 

@app.post("/generate-audio")
async def generate_audio(payload: TTSRequest):
    client = Murf(api_key = os.getenv("MURF_API_KEY"))
    res = client.text_to_speech.generate(
        text=payload.text,
        voice_id=payload.voice_id
    )
    return {"audio_url": res.audio_file}