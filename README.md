# JARVIS — Gemini-powered personal AI agent

A Jarvis-style agent, like in Iron Man, built to run on the cloud from a GitHub repo.

**Brain:** Google Gemini (Astra-level: text, vision, voice, tools)
**What it does:**
- Chats in text, remembers you, your preferences and past work
- Sees images / screenshots and describes them (vision)
- Voice in your browser (speech-to-text) + spoken replies (text-to-speech)
- Tools: time, calculator, web search, weather, notes, file listing
- Multi-step tasks, scheduled check-ins, and a simple web UI

## 1. Get a Gemini API key (free tier available)

1. Go to [Google AI Studio](https://aistudio.google.com/apikey)
2. Sign in with Google, click **Create API key**
3. Copy it — you will need it in step 3. Never commit it to GitHub.

## 2. Run it locally

```bash
git clone https://github.com/<your-username>/jarvis-ai.git
cd jarvis-ai
cp .env.example .env
# edit .env and paste your GEMINI_API_KEY
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000 — talk to Jarvis there.

## 3. Push to GitHub

```bash
git init
git add .
git commit -m "Jarvis v1 — Gemini agent"
git branch -M main
git remote add origin https://github.com/<your-username>/jarvis-ai.git
git push -u origin main
```

## 4. Deploy on Render (free tier, stays online)

1. Go to [render.com](https://render.com), sign in with GitHub
2. New → Web Service → pick your `jarvis-ai` repo
3. Render reads `render.yaml` automatically
4. Environment → add `GEMINI_API_KEY` = your key from AI Studio
5. Deploy. You will get a URL like `https://jarvis-ai.onrender.com`

On the free tier Render sleeps after inactivity — first reply after a sleep takes ~30 seconds. A paid instance stays awake.

## 5. Config

| Variable | Default | What it does |
|---|---|---|
| `GEMINI_API_KEY` | — | **Required.** Your Google AI Studio key |
| `GEMINI_MODEL` | `gemini-3.8-flash` | Primary Gemini model. If it returns 503 (busy/high demand), Jarvis retries once after ~1.5s, then falls back in order to gemini-3.7-flash → gemini-3.6-flash → gemini-3.5-flash → gemini-2.5-flash. If all are busy it replies that the AI is busy — it never shows raw API errors. |
| `JARVIS_NAME` | `JARVIS` | The name Jarvis calls itself |
| `USER_NAME` | `Sir` | What Jarvis calls you |

## Files

- `app/main.py` — FastAPI server + web UI + API endpoints
- `app/agent.py` — Gemini brain, tools, vision
- `app/memory.py` — long-term memory saved in `data/memory.json`
- `app/tools.py` — tools Jarvis can call (time, calc, search, weather, notes)
- `static/index.html` — chat UI with voice + image upload
- `render.yaml` / `Dockerfile` — cloud deploy

## Safety

- Private use only. Jarvis has no access to your accounts unless you add those tools yourself.
- Never share your `GEMINI_API_KEY`. If it leaks, delete it in AI Studio and make a new one.
- Jarvis can browse and make files, but it will not post, pay for, or send anything on your behalf without you telling it to.
