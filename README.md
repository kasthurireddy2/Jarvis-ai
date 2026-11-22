# JARVIS — Gemini-powered personal AI agent

A Jarvis-style agent, like in Iron Man, built to run on the cloud from a GitHub repo. Open source under the MIT license — use it, fork it, make it yours.

**Brain:** Google Gemini (Astra-level: text, vision, voice, tools)
**What it does:**
- Chats in text, remembers you, your preferences and past work
- Sees images / screenshots and describes them (vision)
- Voice in your browser (speech-to-text) + spoken replies (text-to-speech)
- Tools: time, date, calculator, web search, news, weather, jokes, translate, currency, notes, reminders, LinkedIn posting
- Permanent memory (Upstash Redis) — facts survive redeploys
- Multi-step tasks and a premium Iron Man HUD web UI

## Memory — command words

Tell Jarvis anything with these, and he saves it to permanent memory
(Upstash Redis when configured, otherwise the local file):

- `remember this: my favourite colour is blue`
- `don't forget my sister's birthday is 12th December`
- `remember to call mom tomorrow` — saved as a reminder
- `remember my name is Kasthuri` — also works, saves "my name is Kasthuri"
- `forget my favourite colour` — removes matching saved facts
- `what do you remember?` — reads it all back

Every Gemini call has a 30s per-model timeout and a 2-minute overall
deadline, so a stalled model falls through to the next one instead of
leaving chat stuck on "thinking..." forever.

## LinkedIn posting

Jarvis can post to your LinkedIn profile — say "post to LinkedIn: ..." or
use the `post_to_linkedin` tool. It needs `LINKEDIN_ACCESS_TOKEN` (OAuth
token with the `w_member_social` scope) in Render env vars; your profile ID
is fetched automatically. Getting the token means creating a LinkedIn
developer app — see the setup steps in the LinkedIn docs, or ask Muse and
he'll walk you through it. There is also a `POST /api/post-linkedin`
endpoint (guarded by `JARVIS_POST_SECRET`) for scheduled posting without
going through Gemini.

- `POST /api/post-linkedin-image` — same guard, body `{"text", "image_url",
  "alt_text" (optional), "secret"}`. The image is downloaded server-side
  from the public URL (max 8 MB), uploaded to LinkedIn, and attached to
  the post.
- `POST /api/delete-linkedin-post` — same guard, body `{"post", "secret"}`,
  where `post` is the post URN (`urn:li:share:...`) or a bare post id.

## 1. Get a Gemini API key (free tier available)

1. Go to [Google AI Studio](https://aistudio.google.com/apikey)
2. Sign in with Google, click **Create API key**
3. Copy it — you will need it in step 3. Never commit it to GitHub.

## 2. Run it locally

```bash
git clone https://github.com/kasthurireddy2/Jarvis-ai.git
cd Jarvis-ai
cp .env.example .env
# edit .env and paste your GEMINI_API_KEY
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000 — talk to Jarvis there.

## Contributing

Found a bug or want a new tool? Fork the repo, make your change, and open a
pull request. Ideas welcome — especially new tools, better voice handling,
and UI improvements. If you like the project, give it a star ⭐.

## 3. Deploy on Render (free tier, stays online)

1. Go to [render.com](https://render.com), sign in with GitHub
2. New → Web Service → pick your `jarvis-ai` repo
3. Render reads `render.yaml` automatically
4. Environment → add `GEMINI_API_KEY` = your key from AI Studio
5. Deploy. You will get a URL like `https://jarvis-ai.onrender.com`

On the free tier Render sleeps after inactivity — first reply after a sleep takes ~30 seconds. A paid instance stays awake.

## 4. Config

| Variable | Default | What it does |
|---|---|---|
| `GEMINI_API_KEY` | — | **Required.** Your Google AI Studio key |
| `GEMINI_MODEL` | `gemini-3.8-flash` | Primary Gemini model. If it returns 503/504 (busy/high demand), Jarvis falls through in order to gemini-3.7-flash → gemini-3.6-flash → gemini-3.5-flash, each with a 30s timeout and a 2-minute overall cap. If all are busy it replies that the AI is busy — it never shows raw API errors. (gemini-2.5-flash was removed: retired for new users.) |
| `JARVIS_TIMEZONE` | `Asia/Kolkata` | Timezone used for time/date answers. |
| `UPSTASH_REDIS_REST_URL` / `UPSTASH_REDIS_REST_TOKEN` | — | **Permanent memory (free Upstash Redis).** Set both in Render env vars and Jarvis remembers facts forever, across redeploys. Without them it falls back to local `data/memory.json`, which Render wipes on redeploy. |
| `JARVIS_NAME` | `JARVIS` | The name Jarvis calls itself |
| `JARVIS_POST_SECRET` | — | Secret guarding `POST /api/post-linkedin` (scheduled posting). Set the same value in the request body and in Render env vars. |
| `USER_NAME` | `Sir` | What Jarvis calls you |

## Files

- `app/main.py` — FastAPI server + web UI + API endpoints
- `app/agent.py` — Gemini brain, tools, vision
- `app/memory.py` — long-term memory: permanent in Upstash Redis when configured, else `data/memory.json`
- `app/tools.py` — tools Jarvis can call (time, calc, search, weather, notes)
- `static/index.html` — chat UI with voice + image upload
- `render.yaml` / `Dockerfile` — cloud deploy

## Safety

- Jarvis has no access to your accounts unless you add those tools yourself.
- Never share your `GEMINI_API_KEY` or any access token. If one leaks, revoke it and make a new one.
- Jarvis can browse and make files, but it will not post, pay for, or send anything on your behalf without you telling it to.

## License

MIT — see [LICENSE](LICENSE).
