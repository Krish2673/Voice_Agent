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