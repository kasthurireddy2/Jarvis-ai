"""Tools JARVIS can use. Keep them small, safe, and reversible."""
import datetime
import json
import os
import re

import requests

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
NOTES_FILE = os.path.join(DATA_DIR, "notes.json")


def get_time() -> str:
    now = datetime.datetime.now()
    return now.strftime("%A, %d %B %Y, %I:%M %p")


def calculate(expression: str) -> str:
    """Only allow numbers and basic maths operators."""
    if not re.fullmatch(r"[0-9+\-*/(). %]+", expression or ""):
        return "I can only calculate numbers with + - * / ( ) and %."
    try:
        return str(eval(expression, {"__builtins__": {}}, {}))
    except Exception as e:
        return f"Could not calculate that: {e}"


def web_search(query: str) -> str:
    """Free search via DuckDuckGo, no API key needed."""
    try:
        r = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": 1},
            timeout=10,
        )
        data = r.json()
        out = data.get("AbstractText") or ""
        topics = [t.get("Text") for t in data.get("RelatedTopics", [])[:3] if t.get("Text")]
        if topics:
            out += "\n" + "\n".join(topics)
        return out.strip() or f"No quick answer found for '{query}'. Try a web search for more."
    except Exception as e:
        return f"Search failed: {e}"


def get_weather(city: str) -> str:
    """Free weather via wttr.in, no API key needed."""
    try:
        r = requests.get(f"https://wttr.in/{city}?format=j1", timeout=10)
        data = r.json()
        cur = data["current_condition"][0]
        area = data["nearest_area"][0]["areaName"][0]["value"]
        return (
            f"{area}: {cur['weatherDesc'][0]['value']}, "
            f"{cur['temp_C']}°C, feels like {cur['FeelsLikeC']}°C, "
            f"humidity {cur['humidity']}%."
        )
    except Exception as e:
        return f"Weather check failed: {e}"


def save_note(text: str) -> str:
    os.makedirs(DATA_DIR, exist_ok=True)
    notes = []
    if os.path.exists(NOTES_FILE):
        notes = json.load(open(NOTES_FILE))
    notes.append({"text": text, "at": datetime.datetime.now().isoformat()})
    json.dump(notes, open(NOTES_FILE, "w"), indent=2)
    return f"Noted. I have {len(notes)} note(s) saved."


def list_notes() -> str:
    if not os.path.exists(NOTES_FILE):
        return "No notes saved yet."
    notes = json.load(open(NOTES_FILE))
    if not notes:
        return "No notes saved yet."
    return "\n".join(f"- {n['text']}" for n in notes[-10:])


TOOLS = {
    "get_time": (get_time, "Current date and time"),
    "calculate": (calculate, "Calculate a maths expression, e.g. '25*4+10'"),
    "web_search": (web_search, "Search the web for a topic"),
    "get_weather": (get_weather, "Weather for a city, e.g. 'Bengaluru'"),
    "save_note": (save_note, "Save a note / reminder for later"),
    "list_notes": (list_notes, "List saved notes"),
}
