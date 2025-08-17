from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.websocket("/ws")
async def websocket_endpoint(websocket : WebSocket):
    await websocket.accept()
    logger.info("Client connected to /ws")
    
    try:
        while True:
            data = await websocket.receive_text()
            logger.info(f"Message received: {data}")

            await websocket.send_text(f"Echo: {data}")

    except WebSocketDisconnect:
        logger.info("Client disconnected from /ws")

@router.websocket("/agent/chat/{session_id}")
async def websocket_chat(websocket : WebSocket, session_id : str):
    await websocket.accept()
    logger.info(f"Client connected with session: {session_id}")

    try:
        with open(f"received_audio_{session_id}.webm", "wb") as f:
            while True:
                data = await websocket.receive()

                if "bytes" in data:
                    f.write(data["bytes"])

                elif "text" in data:
                    msg = data["text"]
                    logger.info(f"Text msg from {session_id}: {msg}")

    except WebSocketDisconnect:
        logger.info(f"Client {session_id} disconnected")