"""JARVIS web server — chat, vision, voice-ready UI, health check."""
import hmac
import os

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .agent import JARVIS_NAME, chat, describe_image
from .linkedin_tool import delete_linkedin_post, post_to_linkedin, post_to_linkedin_with_image
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


def _check_post_secret(payload: dict):
    """Shared guard for the LinkedIn endpoints. Returns an error
    JSONResponse, or None when the caller may proceed. If the env var is
    not set, the endpoints stay closed (503)."""
    secret = os.environ.get("JARVIS_POST_SECRET")
    if not secret:
        return JSONResponse({"error": "LinkedIn posting endpoint is not configured."}, status_code=503)
    provided = (payload or {}).get("secret", "")
    if not isinstance(provided, str) or not hmac.compare_digest(provided, secret):
        return JSONResponse({"error": "Unauthorized."}, status_code=401)
    return None


@app.post("/api/post-linkedin")
def api_post_linkedin(payload: dict):
    """Direct LinkedIn posting for the scheduled daily post.

    Deliberately does NOT go through Gemini: the daily 10am post must go
    out even when Gemini is overloaded. Guarded by JARVIS_POST_SECRET —
    the same value must be sent as `secret` in the request body and set
    as the JARVIS_POST_SECRET env var in Render. If the env var is not
    set, the endpoint stays closed (503).
    """
    err = _check_post_secret(payload)
    if err:
        return err
    text = ((payload or {}).get("text", "") or "").strip()
    if not text:
        return JSONResponse({"error": "Empty post text."}, status_code=400)
    return {"result": post_to_linkedin(text)}


@app.post("/api/post-linkedin-image")
def api_post_linkedin_image(payload: dict):
    """Post to LinkedIn with an image attached. Same secret guard as
    /api/post-linkedin. Body: {"text", "image_url", "alt_text" (optional),
    "secret"}. The image is downloaded server-side from image_url."""
    err = _check_post_secret(payload)
    if err:
        return err
    text = ((payload or {}).get("text", "") or "").strip()
    if not text:
        return JSONResponse({"error": "Empty post text."}, status_code=400)
    image_url = ((payload or {}).get("image_url", "") or "").strip()
    if not image_url:
        return JSONResponse({"error": "Empty image_url."}, status_code=400)
    alt_text = ((payload or {}).get("alt_text", "") or "").strip()
    return {"result": post_to_linkedin_with_image(text, image_url, alt_text)}


@app.post("/api/delete-linkedin-post")
def api_delete_linkedin_post(payload: dict):
    """Delete a LinkedIn post. Same secret guard as /api/post-linkedin.
    Body: {"post" (post URN like urn:li:share:... or a bare id), "secret"}."""
    err = _check_post_secret(payload)
    if err:
        return err
    post = ((payload or {}).get("post", "") or "").strip()
    if not post:
        return JSONResponse({"error": "Empty post reference."}, status_code=400)
    return {"result": delete_linkedin_post(post)}


app.mount("/static", StaticFiles(directory=os.path.join(BASE, "static")), name="static")
