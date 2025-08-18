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
from dotenv import load_dotenv
import logging, os, asyncio, subprocess

load_dotenv()
aai.settings.api_key = os.getenv("AssemblyAI_API_KEY")

router = APIRouter()
logger = logging.getLogger(__name__)

# def convert_to_pcm16(audio_bytes: bytes) -> bytes:
#     process = subprocess.Popen(
#         ["ffmpeg", "-i", "pipe:0", "-f", "s16le", "-acodec", "pcm_s16le",
#          "-ac", "1", "-ar", "16000", "pipe:1"],
#         stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
#     )
#     pcm_data, _ = process.communicate(input=audio_bytes)
#     return pcm_data

@router.websocket("/agent/chat/{session_id}")
async def websocket_chat(websocket : WebSocket, session_id : str):
    await websocket.accept()
    logger.info(f"Client connected with session: {session_id}")

    client = StreamingClient(
    StreamingClientOptions(api_key=aai.settings.api_key)
    )

    def on_turn(client, event):
        logger.info(f"[Transcript] {event.transcript} (end_of_turn={event.end_of_turn})")

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