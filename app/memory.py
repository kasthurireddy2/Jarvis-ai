"""Long-term memory: facts and preferences.

Permanent storage is Upstash Redis (free tier) via its REST API, when
UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN are set — Render's
filesystem is ephemeral, so the local JSON file alone does not survive a
redeploy. Without those env vars (or if Redis is unreachable) it falls
back to the local JSON file, so Jarvis keeps working either way.

Facts are stored in the Redis list "jarvis_memories" (RPUSH / LRANGE),
exactly as the Upstash REST API expects.
"""
import json
import os
import urllib.request
import urllib.error

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
MEMORY_FILE = os.path.join(DATA_DIR, "memory.json")

REDIS_URL = os.environ.get("UPSTASH_REDIS_REST_URL")
REDIS_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
MEMORIES_KEY = "jarvis_memories"


def redis_enabled() -> bool:
    """True when Upstash Redis credentials are configured."""
    return bool(REDIS_URL and REDIS_TOKEN)


def _redis_cmd(command: list):
    """Run one command against the Upstash Redis REST API.

    Returns the "result" field, or None on any failure (never raises —
    memory must never crash a chat reply).
    """
    if not redis_enabled():
        return None
    try:
        req = urllib.request.Request(
            REDIS_URL,
            data=json.dumps(command).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {REDIS_TOKEN}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=5) as res:
            return json.loads(res.read().decode("utf-8")).get("result")
    except Exception:
        return None


def save_memory(fact: str) -> str:
    """Saves an important fact about the user permanently (Redis)."""
    if redis_enabled():
        _redis_cmd(["RPUSH", MEMORIES_KEY, fact])
        return f"Saved to permanent memory: {fact}"
    remember_fact(fact)
    return f"Saved to memory: {fact}"


def get_all_memories() -> list:
    """Fetches all stored memories from cloud storage (Redis)."""
    if redis_enabled():
        return _redis_cmd(["LRANGE", MEMORIES_KEY, 0, -1]) or []
    return load_memory()["facts"]


def forget_fact(text: str) -> int:
    """Remove saved facts containing `text` (case-insensitive substring).

    Returns how many facts were removed. Removes from Redis (LREM by exact
    stored value) and from the local mirror.
    """
    needle = (text or "").strip().lower()
    if not needle:
        return 0
    removed = 0
    if redis_enabled():
        for fact in get_all_memories():
            if needle in fact.lower():
                _redis_cmd(["LREM", MEMORIES_KEY, 0, fact])
                removed += 1
    local = _load_local()
    kept = [f for f in local["facts"] if needle not in f.lower()]
    local_removed = len(local["facts"]) - len(kept)
    if local_removed:
        local["facts"] = kept
        _save_local(local)
    # Redis and local mirror hold the same facts, so the distinct count is the max.
    return max(removed, local_removed)


def _load_local() -> dict:
    if not os.path.exists(MEMORY_FILE):
        return {"facts": [], "preferences": []}
    try:
        data = json.load(open(MEMORY_FILE))
        return {
            "facts": data.get("facts", []),
            "preferences": data.get("preferences", []),
        }
    except Exception:
        return {"facts": [], "preferences": []}


def _save_local(memory: dict) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    json.dump(memory, open(MEMORY_FILE, "w"), indent=2)


def load_memory() -> dict:
    """Facts come from Redis when configured, else from the local file.

    Preferences are still kept locally for now.
    """
    local = _load_local()
    if redis_enabled():
        facts = get_all_memories()
        if facts:  # Redis reachable and has memories — trust it
            return {"facts": facts, "preferences": local["preferences"]}
        # Redis empty/unreachable: fall back to local facts so nothing is lost
    return local


def remember_fact(fact: str) -> None:
    """Remember one durable fact, in Redis when configured, else locally."""
    if not fact:
        return
    if redis_enabled():
        existing = get_all_memories()
        if fact not in existing:
            _redis_cmd(["RPUSH", MEMORIES_KEY, fact])
        # Also mirror locally, so a Redis outage never loses the fact.
        local = _load_local()
        if fact not in local["facts"]:
            local["facts"].append(fact)
            _save_local(local)
        return
    local = _load_local()
    if fact not in local["facts"]:
        local["facts"].append(fact)
        _save_local(local)


def memory_text() -> str:
    memory = load_memory()
    lines = []
    if memory["facts"]:
        lines.append("Facts about the user:\n- " + "\n- ".join(memory["facts"]))
    if memory["preferences"]:
        lines.append("Preferences:\n- " + "\n- ".join(memory["preferences"]))
    return "\n".join(lines) or "No long-term memory yet."
