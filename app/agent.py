"""JARVIS brain — Google Gemini, with tools, memory and vision."""
import base64
import os

from dotenv import load_dotenv

from .memory import memory_text, remember_fact
from .tools import TOOLS

load_dotenv()

JARVIS_NAME = os.getenv("JARVIS_NAME", "JARVIS")
USER_NAME = os.getenv("USER_NAME", "Sir")
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
API_KEY = os.getenv("GEMINI_API_KEY", "")

SYSTEM_PROMPT = f"""You are {JARVIS_NAME}, a personal AI agent like Jarvis in Iron Man.
You talk to {USER_NAME}. Be warm, direct, a little witty, and practical.
You can see images, hear voice (transcribed by the browser), and use tools.
Use tools when a question needs a live fact: time, weather, web search, maths, notes.
If you learn a durable fact about the user (name, preference, goal), say so briefly
and remember it with the remember tool in your head — in this code that is done
by the server when you reply starting with 'REMEMBER: '.
Keep answers short in chat, longer only when the user asks for detail.
Never invent a booking, payment, or message sent on the user's behalf.
"""

_client = None


def get_client():
    global _client
    if _client is None:
        if not API_KEY:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Get one at https://aistudio.google.com/apikey "
                "and put it in .env (local) or in Render environment variables (cloud)."
            )
        from google import genai

        _client = genai.Client(api_key=API_KEY)
    return _client


def _run_tools_if_asked(reply: str) -> str:
    """Simple tool loop: if Gemini asks for a tool in [TOOL:name:args] form, run it."""
    # Gemini usually answers directly; this keeps tools working even in plain text mode.
    # Format the model is told to use: [TOOL:web_search:query]
    import re

    extra = []
    for match in re.finditer(r"\[TOOL:([a-z_]+):([^\]]+)\]", reply):
        name, arg = match.group(1), match.group(2).strip()
        if name in TOOLS:
            fn, _ = TOOLS[name]
            try:
                result = fn(arg) if arg else fn()
            except TypeError:
                result = fn()
            extra.append(f"[{name} result: {result}]")
    if extra:
        return reply + "\n\n" + "\n".join(extra)
    return reply


def chat(message: str, history: list[dict] | None = None) -> str:
    client = get_client()
    tool_list = "\n".join(f"- {name}: {desc}" for name, (_, desc) in TOOLS.items())
    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Memory:\n{memory_text()}\n\n"
        f"Tools you can use (reply with [TOOL:name:args] when you need one):\n{tool_list}\n\n"
        f"User: {message}\n{JARVIS_NAME}:"
    )
    response = client.models.generate_content(model=MODEL, contents=prompt)
    reply = response.text or "I did not get a reply from Gemini, Sir. Please try again."
    reply = _run_tools_if_asked(reply)
    if reply.startswith("REMEMBER: "):
        remember_fact(reply[len("REMEMBER: "):].strip())
    return reply


def describe_image(image_bytes: bytes, mime_type: str, question: str = "What is in this image?") -> str:
    """Vision: Gemini sees the image, like Google Astra."""
    client = get_client()
    from google.genai import types

    response = client.models.generate_content(
        model=MODEL,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            question,
        ],
    )
    return response.text or "I could not see anything in that image, Sir."
