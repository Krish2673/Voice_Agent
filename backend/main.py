from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from backend.utils.logger import setup_logger
from backend.routes import agent, ws, news

logger = setup_logger()

app = FastAPI(title="Conversational Agent")
app.mount("/static", StaticFiles(directory="frontend"), name="static")

app.include_router(agent.router, prefix="/agent", tags=["Agent"])
app.include_router(ws.router, tags = ["Websocket"])
app.include_router(news.router, prefix = "/api")

@app.get("/", response_class=HTMLResponse)
async def get_index():
    with open("frontend/index.html", "r") as f:
        return f.read()
