from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse, Response
from backend.schemas.chat_schemas import ChatResponse, ErrorResponse
from backend.services.stt_service import transcribe_audio
from backend.services.llm_service import generate_llm_response
from backend.services.tts_service import text_to_speech
import logging

router = APIRouter()

chat_histories = {}
logger = logging.getLogger("chatbot")

@router.post("/chat/{session_id}", response_model=ChatResponse, responses={500: {"model": ErrorResponse}})
async def agent_chat(session_id: str, file: UploadFile = File(...)):
    try:
        audio_bytes = await file.read()
        user_text = transcribe_audio(audio_bytes)

        if not user_text.strip():
            return Response(status_code=204)

        if session_id not in chat_histories:
            chat_histories[session_id] = []
        chat_histories[session_id].append({"role": "user", "content": user_text})

        conversation = "\n".join(f"{m['role'].capitalize()} : {m['content']}" for m in chat_histories[session_id])
        llm_text = generate_llm_response(conversation)

        chat_histories[session_id].append({"role": "assistant", "content": llm_text})

        audio_url = text_to_speech(llm_text)

        return JSONResponse(content={
            "user_transcript": user_text,
            "llm_text": llm_text,
            "audio_url": audio_url,
            "history": chat_histories[session_id]
        })

    except Exception as e:
        logger.error(f"Error in agent_chat: {e}")
        try:
            audio_url = text_to_speech(f"An error occurred: {str(e)}")
            return JSONResponse(content={"error": str(e), "audio_url": audio_url}, status_code=500)
        except Exception as tts_err:
            return JSONResponse(content={"error": f"{str(e)} | TTS Failed: {str(tts_err)}"}, status_code=500)
