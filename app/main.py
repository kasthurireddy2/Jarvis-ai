"""JARVIS web server — chat, vision, voice-ready UI, health check."""
import hmac
import os

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .agent import JARVIS_NAME, chat, describe_image
from .linkedin_tool import post_to_linkedin
from .memory import load_memory, memory_text
from .tools import TOOLS

app = FastAPI(title="JARVIS")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@app.get("/health")
def health():
    return {"status": "ok", "agent": JARVIS_NAME, "model": os.getenv("GEMINI_MODEL", "gemini-3.8-flash")}


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
    # Names for backwards compatibility plus descriptions for the UI.
    return {"tools": [{"name": name, "description": desc} for name, (_, desc) in TOOLS.items()]}


@app.post("/api/post-linkedin")
def api_post_linkedin(payload: dict):
    """Direct LinkedIn posting for the scheduled daily post.

    Deliberately does NOT go through Gemini: the daily 10am post must go
    out even when Gemini is overloaded. Guarded by JARVIS_POST_SECRET —
    the same value must be sent as `secret` in the request body and set
    as the JARVIS_POST_SECRET env var in Render. If the env var is not
    set, the endpoint stays closed (503).
    """
    secret = os.environ.get("JARVIS_POST_SECRET")
    if not secret:
        return JSONResponse({"error": "LinkedIn posting endpoint is not configured."}, status_code=503)
    provided = (payload or {}).get("secret", "")
    if not isinstance(provided, str) or not hmac.compare_digest(provided, secret):
        return JSONResponse({"error": "Unauthorized."}, status_code=401)
    text = ((payload or {}).get("text", "") or "").strip()
    if not text:
        return JSONResponse({"error": "Empty post text."}, status_code=400)
    return {"result": post_to_linkedin(text)}


app.mount("/static", StaticFiles(directory=os.path.join(BASE, "static")), name="static")
