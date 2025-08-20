from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import assemblyai as aai
from assemblyai.streaming.v3 import (
    BeginEvent,
    StreamingClient,
    StreamingClientOptions,
    StreamingError,
    StreamingEvents,
    StreamingParameters,
    StreamingSessionParameters,
    TerminationEvent,
    TurnEvent,
)
import logging, asyncio, subprocess
from google import genai
from backend.utils.config import GEMINI_API_KEY
from backend.utils.config import ASSEMBLYAI_API_KEY

aai.settings.api_key = ASSEMBLYAI_API_KEY

router = APIRouter()
logger = logging.getLogger(__name__)

@router.websocket("/agent/chat/{session_id}")
async def websocket_chat(websocket : WebSocket, session_id : str):
    await websocket.accept()
    logger.info(f"Client connected with session: {session_id}")

    client = StreamingClient(
    StreamingClientOptions(api_key=aai.settings.api_key)
    )

    mainLoop = asyncio.get_event_loop()
    last_transcript = None
    def on_turn(client, event):
        logger.info(f"[Transcript] {event.transcript} (end_of_turn={event.end_of_turn})")

        if event.end_of_turn:
            nonlocal last_transcript
            if last_transcript is None:
                last_transcript = event.transcript
            else:
                asyncio.run_coroutine_threadsafe(
                    websocket.send_text(
                        f'{{"type" : "final_transcript", "text" : "{event.transcript}"}}'
                    ),
                    mainLoop
                )
                asyncio.run_coroutine_threadsafe(
                    websocket.send_text(
                        '{"type" : "turn_end"}'
                    ),
                    mainLoop
                )
                mainLoop.run_in_executor(None, stream_llm_response, event.transcript,websocket,mainLoop)
                last_transcript = None

        else:
            asyncio.run_coroutine_threadsafe(
                websocket.send_text(
                    f'{{"type" : "partial_transcript", "text" : "{event.transcript}"}}'
                ),
                mainLoop
            )

    client.on(StreamingEvents.Turn, on_turn)
    client.on(StreamingEvents.Error, lambda c,e: logger.error(f"Error: {e}"))

    client.connect(StreamingParameters(sample_rate=16000, format_turns=True))

    try:
        while True:
            data = await websocket.receive()

            if "bytes" in data:
                # pcm_chunk = convert_to_pcm16(data["bytes"]) 
                await asyncio.to_thread(client.stream, data["bytes"])
            
            elif "text" in data:
                msg = data["text"]
                logger.info(f"Text msg from {session_id}: {msg}")
                if msg == "end_of_audio":
                    await asyncio.to_thread(client.disconnect)
                    break

    except WebSocketDisconnect:
        logger.info(f"Client {session_id} disconnected")

def stream_llm_response(prompt : str, websocket : WebSocket, mainLoop):
    client = genai.Client(api_key = GEMINI_API_KEY)
    response = client.models.generate_content_stream(
        model = "gemini-2.0-flash",
        contents = prompt
    )
    
    def send_chunks():
        final_text = ""
        print("\n[LLM Response]")
        for chunk in response:
            if chunk.text:
                final_text += chunk.text
                asyncio.run_coroutine_threadsafe(
                    websocket.send_text(
                        f'{{"type": "llm_chunk", "text": "{chunk.text}"}}'
                    ),
                    mainLoop
                )
                print(chunk.text, end="", flush=True)
        asyncio.run_coroutine_threadsafe(
            websocket.send_text('{"type": "llm_end"}'),
            mainLoop
        )
        print("\n" + "-" * 80)

    mainLoop.run_in_executor(None, send_chunks)