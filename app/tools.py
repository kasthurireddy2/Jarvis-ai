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


REMINDERS_FILE = os.path.join(DATA_DIR, "reminders.json")
_START_TIME = datetime.datetime.now()

_JOKES = [
    "Why do programmers prefer dark mode? Because light attracts bugs.",
    "Why did the developer go broke? Because he used up all his cache.",
    "There are only 10 kinds of people: those who understand binary and those who don't.",
    "Why do Java developers wear glasses? Because they don't C#.",
    "A SQL query walks into a bar, sees two tables and asks... 'Mind if I join you?'",
    "Why did the computer go to the doctor? It had a virus.",
    "What is a programmer's favourite hangout spot? The Foo Bar.",
    "Why was the JavaScript developer sad? Because he didn't Node how to Express himself.",
]

_FACTS = [
    "Honey never spoils — archaeologists have tasted 3,000-year-old honey and found it perfectly edible.",
    "Octopuses have three hearts, and two of them stop beating when they swim.",
    "Bananas are berries, but strawberries are not berries.",
    "The first computer bug was a real moth found in a computer in 1947.",
    "Sharks existed before trees — by about 50 million years.",
    "A day on Venus is longer than a year on Venus.",
    "The Eiffel Tower grows about 15 cm taller in summer as the iron expands.",
    "There are more possible chess games than atoms in the observable universe.",
]


def get_date() -> str:
    now = datetime.datetime.now()
    return now.strftime("Today is %A, %d %B %Y.")


def get_news(query: str = "") -> str:
    """Top headlines from Google News RSS (India edition), no API key needed."""
    try:
        url = "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en"
        if query and query.strip():
            url = ("https://news.google.com/rss/search?q=" + requests.utils.quote(query.strip())
                   + "&hl=en-IN&gl=IN&ceid=IN:en")
        r = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
        import xml.etree.ElementTree as ET
        root = ET.fromstring(r.content)
        titles = []
        for item in root.iter("item"):
            t = item.findtext("title")
            if t:
                titles.append(t.strip())
            if len(titles) >= 5:
                break
        if not titles:
            return "No headlines found right now, Sir."
        return "Top headlines:\n" + "\n".join(f"- {t}" for t in titles)
    except Exception:
        return "Sorry, Sir — I could not fetch the news right now. Please try again in a moment."


def joke() -> str:
    day = datetime.date.today().toordinal()
    return _JOKES[day % len(_JOKES)]


def random_fact() -> str:
    day = datetime.date.today().toordinal()
    return _FACTS[day % len(_FACTS)]


def system_status() -> str:
    uptime = datetime.datetime.now() - _START_TIME
    mins = int(uptime.total_seconds() // 60)
    model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    return (f"JARVIS is online, Sir. Model: {model}. "
            f"Uptime this session: {mins} minute(s). Tools available: {len(TOOLS)}.")


def _load_reminders():
    if not os.path.exists(REMINDERS_FILE):
        return []
    try:
        return json.load(open(REMINDERS_FILE))
    except Exception:
        return []


def set_reminder(text: str) -> str:
    if not (text or "").strip():
        return "What should I remind you about, Sir?"
    os.makedirs(DATA_DIR, exist_ok=True)
    reminders = _load_reminders()
    reminders.append({"text": text.strip(), "at": datetime.datetime.now().isoformat()})
    json.dump(reminders, open(REMINDERS_FILE, "w"), indent=2)
    return f"Reminder saved, Sir. I have {len(reminders)} reminder(s) saved."


def list_reminders() -> str:
    reminders = _load_reminders()
    if not reminders:
        return "No reminders saved yet, Sir."
    return "\n".join(f"- {r['text']}" for r in reminders[-10:])


def translate(text: str) -> str:
    """Translate English text. Arg format: 'hello | hi' or 'hello to Hindi' or just 'hello' (defaults to Hindi)."""
    arg = (text or "").strip()
    if not arg:
        return "What should I translate, Sir? Give me the text and the language, e.g. 'good morning to Hindi'."
    target = "hi"
    lang_names = {"hindi": "hi", "telugu": "te", "tamil": "ta", "spanish": "es",
                  "french": "fr", "german": "de", "english": "en", "urdu": "ur"}
    if "|" in arg:
        arg, target = [p.strip() for p in arg.rsplit("|", 1)]
        target = lang_names.get(target.lower(), target.lower())
    elif " to " in arg.lower():
        arg, target = arg.rsplit(" to ", 1)
        arg, target = arg.strip(), target.strip()
        target = lang_names.get(target.lower(), target.lower())
    try:
        r = requests.get("https://api.mymemory.translated.net/get",
                         params={"q": arg, "langpair": f"en|{target}"}, timeout=5)
        data = r.json()
        out = (data.get("responseData") or {}).get("translatedText", "")
        if out:
            return out
        return "Sorry, Sir — I could not translate that right now."
    except Exception:
        return "Sorry, Sir — the translation service did not answer. Please try again in a moment."


def currency_convert(text: str) -> str:
    """Arg like '100 USD to INR' or '100 USD INR'."""
    arg = (text or "").strip()
    m = re.match(r"([\d.]+)\s*([A-Za-z]{3})\s*(?:to\s*)?([A-Za-z]{3})", arg)
    if not m:
        return "Tell me the amount and currencies, Sir — e.g. '100 USD to INR'."
    amount, src, dst = float(m.group(1)), m.group(2).upper(), m.group(3).upper()
    try:
        r = requests.get(f"https://api.exchangerate-api.com/v4/latest/{src}", timeout=5)
        data = r.json()
        rate = (data.get("rates") or {}).get(dst)
        if rate is None:
            return f"Sorry, Sir — I could not find the rate for {src} to {dst}."
        return f"{amount:g} {src} = {amount * rate:,.2f} {dst} (rate: 1 {src} = {rate} {dst})."
    except Exception:
        return "Sorry, Sir — the currency service did not answer. Please try again in a moment."


def define_word(word: str) -> str:
    w = (word or "").strip().split()[0] if (word or "").strip() else ""
    if not w:
        return "Which word should I define, Sir?"
    try:
        r = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{w}", timeout=5)
        data = r.json()
        meanings = (data[0].get("meanings") or []) if isinstance(data, list) and data else []
        if meanings:
            defs = (meanings[0].get("definitions") or [])
            if defs:
                return f"{w}: {defs[0].get('definition', '')}"
        return f"Sorry, Sir — I could not find a definition for '{w}'."
    except Exception:
        return "Sorry, Sir — the dictionary did not answer. Please try again in a moment."


TOOLS = {
    "get_time": (get_time, "Current date and time"),
    "get_date": (get_date, "Today's date and day of the week"),
    "calculate": (calculate, "Calculate a maths expression, e.g. '25*4+10'"),
    "web_search": (web_search, "Search the web for a topic"),
    "get_news": (get_news, "Top news headlines, optionally about a topic"),
    "get_weather": (get_weather, "Weather for a city, e.g. 'Bengaluru'"),
    "joke": (joke, "Tell a clean joke"),
    "random_fact": (random_fact, "Tell an interesting random fact"),
    "define_word": (define_word, "Define an English word, e.g. 'serendipity'"),
    "translate": (translate, "Translate English text, e.g. 'good morning to Hindi'"),
    "currency_convert": (currency_convert, "Convert money, e.g. '100 USD to INR'"),
    "system_status": (system_status, "Check Jarvis status: model, uptime, tools"),
    "save_note": (save_note, "Save a note / reminder for later"),
    "list_notes": (list_notes, "List saved notes"),
    "set_reminder": (set_reminder, "Save a reminder, e.g. 'call mom in 30 minutes'"),
    "list_reminders": (list_reminders, "List saved reminders"),
}
