"""
Where Is My Stuff? — voice assistant for remembering where you left things.
Backend: FastAPI + SQLite.
"""
import os

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from database import delete_item, find_item, get_all_items, init_db, save_item
from nlp import parse_intent

# ─── Security configuration ────────────────────────────────────────────────────

# Shared family key. Set via FAMILY_API_KEY environment variable.
# If it is not set, a default value is used.
FAMILY_API_KEY = os.getenv("FAMILY_API_KEY", "family-kulyk-2026")

print("FAMILY_API_KEY at startup:", repr(FAMILY_API_KEY))


def require_api_key(x_api_key: str = Header(...)) -> None:
    """
    Simple API authentication for family use.

    All "sensitive" endpoints require header:
      X-API-Key: <family_key>

    Note: no alias — FastAPI auto-converts x_api_key → x-api-key,
    Starlette lowercases all incoming headers, so matching is reliable.
    """
    if not FAMILY_API_KEY:
        # Якщо ключ не налаштовано, вважаємо, що доступ заборонений
        raise HTTPException(status_code=500, detail="API key не налаштовано на сервері")

    if x_api_key != FAMILY_API_KEY:
        raise HTTPException(status_code=401, detail="Невірний або відсутній API key")


# ─── FastAPI initialization ───────────────────────────────────────────────────

app = FastAPI(
    title="Де мої речі?",
    description="Голосовий асистент для запам'ятовування місць зберігання речей",
    version="1.0.0",
)

# Initialize the database on app startup
init_db()

# Mount folder with static files (HTML, CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")


# ─── Data models ──────────────────────────────────────────────────────────────

class VoiceRequest(BaseModel):
    """Incoming request with text from microphone."""
    text: str


class VoiceResponse(BaseModel):
    """Response from the server."""
    reply: str                  # Reply text (spoken aloud)
    intent: str | None = None   # Detected intent: save / query / unknown
    item: str | None = None     # Name of found/saved item
    location: str | None = None # Item location


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def serve_frontend():
    """Return the main page with UI."""
    return FileResponse("static/index.html")


@app.post("/voice", response_model=VoiceResponse)
async def process_voice(
    request: VoiceRequest,
    _: None = Depends(require_api_key),
):
    """
    Main endpoint for processing voice commands.

    Examples:
      - "Я поклав ключі на полицю" → saves to the database
      - "Де мої ключі?" → returns location
    """
    text = request.text.strip()

    if not text:
        raise HTTPException(status_code=400, detail="Текст не може бути порожнім")

    # Detect user intent
    result = parse_intent(text)
    intent = result.get("intent", "unknown")

    # ── Intent: save item ─────────────────────────────────────────────────────
    if intent == "save":
        item = result["item"]
        location = result["location"]

        action = save_item(item, location)

        if action == "updated":
            reply = f"Зрозумів! Оновив місце для «{item}»: тепер {location}."
        else:
            reply = f"Запам'ятав! «{item.capitalize()}» знаходяться {location}."

        return VoiceResponse(
            reply=reply,
            intent="save",
            item=item,
            location=location,
        )

    # ── Intent: query item ────────────────────────────────────────────────────
    elif intent == "query":
        item = result["item"]
        found = find_item(item)

        if found:
            return VoiceResponse(
                reply=f"«{found['item'].capitalize()}» знаходяться {found['location']}.",
                intent="query",
                item=found["item"],
                location=found["location"],
            )
        else:
            return VoiceResponse(
                reply=(
                    f"Не знаю, де зараз «{item}». "
                    "Спробуйте спочатку сказати, де ви їх поклали."
                ),
                intent="query",
                item=item,
            )

    # ── Intent: unknown ───────────────────────────────────────────────────────
    else:
        return VoiceResponse(
            reply=(
                "Не зрозумів команду. Спробуйте:\n"
                "• «Я поклав ключі на полицю» — щоб запам'ятати\n"
                "• «Де мої ключі?» — щоб знайти"
            ),
            intent="unknown",
        )


@app.get("/items")
async def list_items(
    _: None = Depends(require_api_key),
):
    """Return all saved items (for viewing/debugging)."""
    return {"items": get_all_items()}


@app.delete("/items/{item_id}")
async def remove_item(
    item_id: int,
    _: None = Depends(require_api_key),
):
    """Delete a record by ID."""
    success = delete_item(item_id)
    if not success:
        raise HTTPException(status_code=404, detail="Запис не знайдено")
    return {"message": "Видалено успішно"}
