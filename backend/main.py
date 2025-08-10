from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from murf import Murf
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from pathlib import Path
import assemblyai as aai
from google import genai

load_dotenv()

aai.settings.api_key = os.getenv("AssemblyAI_API_KEY")

uploadDIR = Path("uploads")
uploadDIR.mkdir(exist_ok = True)

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

@app.post("/upload-audio")
async def upload_audio(file : UploadFile = File(...)):
    file_path = uploadDIR/file.filename

    with open(file_path,"wb") as f:
        content = await file.read()
        f.write(content)

    return {
        "filename" : file.filename,
        "content_type" : file.content_type,
        "size_kb" : round(len(content)/1024,2)
    }

@app.post("/transcribe/file")
async def transcribe_file(file : UploadFile = File(...)):
    file_content = await file.read()

    transcriber =  aai.Transcriber()
    transcript = transcriber.transcribe(file_content)

    return JSONResponse(content = {"transcript" : transcript.text})

@app.post("/tts/echo")
async def tts_echo(file : UploadFile = File(...)):
    file_content = await file.read()

    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(file_content)
    text = transcript.text

    client = Murf(api_key = os.getenv("MURF_API_KEY"))
    res = client.text_to_speech.generate(
        text = text,
        voice_id = "en-US-terrell"
    )
    return {"audio_url" : res.audio_file, "transcript" : text}

class LLMRequest(BaseModel):
    prompt:str

@app.post("/llm/query")
async def llm_query(file : UploadFile = File(...)):
    try:
        file_content = await file.read()    #read audio file

        transcriber = aai.Transcriber()         #Transcribe using Assesmbly AI
        transcript = transcriber.transcribe(file_content)
        user_text = transcript.text

        client = genai.Client(api_key = os.getenv("Gemini_API_KEY"))        #Send Transcription to Gemini LLM
        response = client.models.generate_content(
            model = "gemini-2.5-flash",
            contents = user_text 
        )
        llm_text = response.text

        murf_client = Murf(api_key = os.getenv("MURF_API_KEY"))         # Send LLM Response to Murf tts
        murf_res = murf_client.text_to_speech.generate(
            text = llm_text,
            voice_id = "en-US-terrell"
        )

        return JSONResponse(content = {                     # return text + audio
            "user_transcript" : user_text,
            "llm_text" : llm_text,
            "audio_url" : murf_res.audio_file
        })
    
    except Exception as e:
        return JSONResponse(content = {"error" : str(e)}, status_code = 500)