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
# from backend.utils.config import GEMINI_API_KEY, ASSEMBLYAI_API_KEY, MURF_API_KEY
from google.genai import types
import re, httpx

# aai.settings.api_key = ASSEMBLYAI_API_KEY

router = APIRouter()
logger = logging.getLogger(__name__)

STATIC_CONTEXT_ID = "day23-convo-agent"

chat_history_store = {}
user_keys = {}

@router.websocket("/agent/chat/{session_id}")
async def websocket_chat(websocket : WebSocket, session_id : str):
    await websocket.accept()
    logger.info(f"Client connected with session: {session_id}")

    if session_id not in chat_history_store:
        chat_history_store[session_id] = []

    user_keys = {
        "gemini": None,
        "murf": None,
        "assembly": None,
    }

    async def handle_config(msg):
        nonlocal user_keys
        if "keys" in msg:
            for k, v in msg["keys"].items():
                if v:  # override only if user entered
                    user_keys[k] = v
            logger.info(f"Updated API keys for session {session_id}")

        if not all(user_keys.values()):
            await websocket.send_text(json.dumps({
                "type": "error",
                "text": "Missing API keys. Please provide Gemini, AssemblyAI, and Murf keys before continuing."
            }))
            return False
        return True
    
    if not user_keys["assembly"]:
        await websocket.send_text(json.dumps({
            "type": "error",
            "text": "AssemblyAI key missing. Please configure your API keys."
        }))
        return

    client = StreamingClient(
    StreamingClientOptions(api_key = user_keys["assembly"])
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
                
                if isinstance(msg, dict) and msg.get("type") == "config_keys":
                    await handle_config(msg)
                    continue
                
                if msg == "end_of_audio":
                    await websocket.send_text(json.dumps({"type": "end_of_audio"}))
                    await asyncio.to_thread(client.disconnect)
                    break

    except WebSocketDisconnect:
        logger.info(f"Client {session_id} disconnected")

def stream_llm_response(session_id : str, prompt : str, websocket : WebSocket, mainLoop):
    if not user_keys["gemini"]:
        asyncio.run_coroutine_threadsafe(
            websocket.send_text(json.dumps({
                "type": "error",
                "text": "Gemini API key missing. Please configure your API keys."
            })),
            mainLoop
        )
        return
    
    client = genai.Client(api_key = user_keys["gemini"])

    conversation = chat_history_store.get(session_id, [])
    conversation.append({"role" : "user", "content" : prompt})

    response = client.models.generate_content_stream(
        model = "gemini-2.0-flash",
        config = types.GenerateContentConfig(
            system_instruction = """You are Glitzo, a witty software developer AI with a playful and pun-loving personality.
                You explain things in a tech-savvy, humorous way, using coding metaphors, programming jokes, and occasional clever puns.
                Keep the tone friendly, casual, and geeky — like a developer friend who makes conversations fun while giving helpful advice.
                Whenever appropriate, sprinkle in small programming references or jokes related to code, bugs, or debugging.
                
                Special Skill: 
                If the user asks for the latest tech news, do NOT make it up. Instead, respond with:
                'Let me fetch the latest commits from the world of tech news for you... 📰💻'
                Then, call the /api/news/tech endpoint (limit=5) and present the results in a fun developer tone"""),
        contents = [prompt]
    )
    
    async def send_to_murf(text : str, websocket : WebSocket, mainLoop):
        if not user_keys["murf"]:
            await websocket.send_text(json.dumps({
                "type": "error",
                "text": "Murf API key missing. Please configure your API keys."
            }))
            return
    
        MURF_WS_URL = f"wss://api.murf.ai/v1/speech/stream-input?api_key={user_keys['murf']}" 

        async with websockets.connect(MURF_WS_URL) as ws:
            await ws.send(json.dumps({
                "context_id": STATIC_CONTEXT_ID,
                "voice_id":"en-US-jayden",
                "style":"Friendly",
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

    if re.search(r"\b(news|tech news|latest updates|headlines)\b", prompt.lower()):
        async def fetch_and_send_news():
            # 1. Let user know
            intro = "Let me fetch the latest commits from the world of tech news for you... 📰💻"
            await websocket.send_text(json.dumps({"type": "llm_chunk", "text": intro}))
            
            async with httpx.AsyncClient() as client_http:
                resp = await client_http.get("http://localhost:8000/api/news/tech?limit=5&randomize=true")
                data = resp.json()
                news_items = data.get("news", [])

            # 2. Send news one by one
            final_text = intro + "\n\n"
            murf_text = intro + "\n\n"

            for i, item in enumerate(news_items, 1):
                title = item['title']
                url = item['url']

                # msg_text = f"{i}. {item['title']}"
                msg_ui = f'{i}. <a href="{url}" target="_blank" style="color: #FFD700; text-decoration: underline;">{title}</a>'
                await websocket.send_text(json.dumps({"type": "llm_chunk", "text": msg_ui}))
                final_text += msg_ui + "\n\n"

                summary_resp = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=[f"Summarize this news headline in 1-2 short, friendly sentences: {title}"]
                )
                summary = summary_resp.text.strip() if summary_resp.text else title

                murf_text += f"{i}. {summary}...\n\n"

            # 3. Wrap up
            outro = "That’s the newsfeed debugged for you! 🚀"
            final_text += outro
            murf_text += outro
            await websocket.send_text(json.dumps({"type": "llm_chunk", "text": outro}))
            await websocket.send_text('{"type": "llm_end"}')

            # Save in history
            chat_history_store[session_id].append({"role": "llm", "content": final_text})

            # 4. Send to Murf
            await send_to_murf(murf_text, websocket, mainLoop)

        asyncio.run(fetch_and_send_news())
        return  # stop here — don't call Gemini
    # --- End Special Skill ---

    def send_chunks():
        final_text = ""
        print("\n[LLM Response]")
        for chunk in response:
            if chunk.text:
                final_text += chunk.text
                asyncio.run_coroutine_threadsafe(
                    websocket.send_text(
                        json.dumps({"type": "llm_chunk", "text": chunk.text})
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