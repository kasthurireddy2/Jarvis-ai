"""Simple long-term memory: facts and preferences, saved as JSON."""
import json
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
MEMORY_FILE = os.path.join(DATA_DIR, "memory.json")


def load_memory() -> dict:
    if not os.path.exists(MEMORY_FILE):
        return {"facts": [], "preferences": []}
    try:
        return json.load(open(MEMORY_FILE))
    except Exception:
        return {"facts": [], "preferences": []}


def save_memory(memory: dict) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    json.dump(memory, open(MEMORY_FILE, "w"), indent=2)


def remember_fact(fact: str) -> None:
    memory = load_memory()
    if fact not in memory["facts"]:
        memory["facts"].append(fact)
        save_memory(memory)


def memory_text() -> str:
    memory = load_memory()
    lines = []
    if memory["facts"]:
        lines.append("Facts about the user:\n- " + "\n- ".join(memory["facts"]))
    if memory["preferences"]:
        lines.append("Preferences:\n- " + "\n- ".join(memory["preferences"]))
    return "\n".join(lines) or "No long-term memory yet."
