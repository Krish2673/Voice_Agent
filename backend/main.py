from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from murf import Murf
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from pathlib import Path
import assemblyai as aai
from google import genai
from typing import List,Dict

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
    
chat_histories : Dict[str,List[Dict[str,str]]] = {}

@app.post("/agent/chat/{session_id}")
async def agent_chat(session_id : str, file : UploadFile = File(...)):
    try:
        file_content = await file.read()        #Transcribe user audio using Assesmbly AI
        transcriber = aai.Transcriber()         
        transcript = transcriber.transcribe(file_content)
        user_text = transcript.text

        if user_text == "":
            return Response(status_code=204)

        if session_id not in chat_histories:            #Store user msgs
            chat_histories[session_id] = []
        chat_histories[session_id].append({"role" : "user", "content" : user_text})

        convo_text = ""                                     #Prepare convo for LLM
        for msg in chat_histories[session_id]:
            convo_text += f"{msg['role'].capitalize()} : {msg['content']}\n"

        client = genai.Client(api_key = os.getenv("Gemini_API_KEY"))        #Send chats to Gemini LLM
        response = client.models.generate_content(
            model = "gemini-2.5-flash",
            contents = convo_text 
        )
        llm_text = response.text

        chat_histories[session_id].append({"role" : "assistant", "content" : llm_text})         #Store assistant's reply

        murf_client = Murf(api_key = os.getenv("MURF_API_KEY"))         #Send LLM Response to Murf tts
        murf_res = murf_client.text_to_speech.generate(
            text = llm_text,
            voice_id = "en-US-terrell"
        )

        return JSONResponse(content = {                         #Return Response
            "user_transcript" : user_text,
            "llm_text" : llm_text,
            "audio_url" : murf_res.audio_file,
            "history" : chat_histories[session_id]
        })

    except Exception as e:
        error_msg = f"An error occured : {str(e)}"

        try:
            murf_client = Murf(api_key = os.getenv("MURF_API_KEY"))         #Send LLM Response to Murf tts
            murf_res = murf_client.text_to_speech.generate(
            text = error_msg,
            voice_id = "en-US-terrell"
            )
            return JSONResponse(content = {"error" : error_msg, "audio_url" : murf_res.audio_file}, status_code = 500)
        
        except Exception as murf_error:
            return JSONResponse(content = {"error" : f"{error_msg} | TTS Failed : {str(murf_error)}"}, status_code = 500)