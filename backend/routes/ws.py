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
import logging, asyncio, subprocess, websockets, json, base64
from google import genai
from backend.utils.config import GEMINI_API_KEY, ASSEMBLYAI_API_KEY, MURF_API_KEY

aai.settings.api_key = ASSEMBLYAI_API_KEY

router = APIRouter()
logger = logging.getLogger(__name__)

MURF_WS_URL = f"wss://api.murf.ai/v1/speech/stream-input?api_key={MURF_API_KEY}" 
STATIC_CONTEXT_ID = "day23-convo-agent"

chat_history_store = {}

@router.websocket("/agent/chat/{session_id}")
async def websocket_chat(websocket : WebSocket, session_id : str):
    await websocket.accept()
    logger.info(f"Client connected with session: {session_id}")

    if session_id not in chat_history_store:
        chat_history_store[session_id] = []

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

                chat_history_store[session_id].append({"role":"user", "content" : event.transcript})

                mainLoop.run_in_executor(None, stream_llm_response, session_id, event.transcript,websocket,mainLoop)
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
    client.connect(StreamingParameters(
        sample_rate=16000, 
        format_turns=True, 
        enable_diarization=False,
        word_boost=[],
        filter_profanity=True,
        punctuate=True,
        redaction=False,
        speech_model="default",
        audio_detection_sensitivity="high"
    ))

    try:
        while True:
            data = await websocket.receive()

            if "bytes" in data:
                await asyncio.to_thread(client.stream, data["bytes"])
                await websocket.send_text(json.dumps({
                    "type": "audio_chunk",
                    "data": base64.b64encode(data["bytes"]).decode("utf-8")  # always base64
                }))
            
            elif "text" in data:
                msg = data["text"]
                logger.info(f"Text msg from {session_id}: {msg}")
                if msg == "end_of_audio":
                    await websocket.send_text(json.dumps({"type": "end_of_audio"}))
                    await asyncio.to_thread(client.disconnect)
                    break

    except WebSocketDisconnect:
        logger.info(f"Client {session_id} disconnected")

def stream_llm_response(session_id : str, prompt : str, websocket : WebSocket, mainLoop):
    client = genai.Client(api_key = GEMINI_API_KEY)

    conversation = chat_history_store.get(session_id, [])
    conversation.append({"role" : "user", "content" : prompt})

    response = client.models.generate_content_stream(
        model = "gemini-2.0-flash",
        contents = prompt
    )
    
    async def send_to_murf(text : str, websocket : WebSocket, mainLoop):
        async with websockets.connect(MURF_WS_URL) as ws:
            await ws.send(json.dumps({
                "context_id": STATIC_CONTEXT_ID,
                "voiceId": "en-US-terrel",  # example voice
                "format": "wav",
                "text": text
            }))

            async for msg in ws:
                data = json.loads(msg)

                if "audio" in data:
                    base64_chunk = data["audio"]
                    asyncio.run_coroutine_threadsafe(
                    websocket.send_text(
                        json.dumps({"type": "audio_chunk", "data": base64_chunk})
                    ),
                    mainLoop
                )

                if data.get("event") == "completed":
                    asyncio.run_coroutine_threadsafe(
                        websocket.send_text(json.dumps({"type": "end_of_audio"})),
                        mainLoop
                    )
                    print("[Server] Murf audio stream completed")
                    break

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

        chat_history_store[session_id].append({"role" : "llm", "content" : final_text})

        asyncio.run_coroutine_threadsafe(
            websocket.send_text('{"type": "llm_end"}'),
            mainLoop
        )
        print("\n" + "-" * 80)

        asyncio.run(send_to_murf(final_text,websocket,mainLoop))

    mainLoop.run_in_executor(None, send_chunks)