"""JARVIS web server — chat, vision, voice-ready UI, health check."""
import os

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .agent import JARVIS_NAME, chat, describe_image
from .memory import load_memory, memory_text
from .tools import TOOLS

app = FastAPI(title="JARVIS")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@app.get("/health")
def health():
    return {"status": "ok", "agent": JARVIS_NAME, "model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash")}


@app.get("/")
def home():
    return FileResponse(os.path.join(BASE, "static", "index.html"))


@app.post("/api/chat")
def api_chat(payload: dict):
    message = (payload or {}).get("message", "").strip()
    if not message:
        return JSONResponse({"error": "Empty message"}, status_code=400)
    try:
        return {"reply": chat(message)}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/vision")
async def api_vision(file: UploadFile = File(...), question: str = Form("What is in this image?")):
    data = await file.read()
    try:
        return {"reply": describe_image(data, file.content_type or "image/jpeg", question)}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/memory")
def api_memory():
    return load_memory()


@app.get("/api/tools")
def api_tools():
    return {"tools": [name for name in TOOLS]}


app.mount("/static", StaticFiles(directory=os.path.join(BASE, "static")), name="static")
