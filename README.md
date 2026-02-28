## Where Is My Stuff?

Voice‑controlled assistant (Ukrainian) that remembers where you put things and later tells you where they are.  
Built with **FastAPI**, **SQLite**, and a small custom **NLP** module.

### Features

- **Save locations** with natural phrases like:  
  “Я поклав ключі на полицю”
- **Ask for locations**:  
  “Де мої ключі?”, “Де мій паспорт?”
- **Fuzzy item search** (handles different word endings, substrings)
- **Simple family‑shared API key** so only your family can modify data
- Minimal web UI with:
  - microphone button (Web Speech API, `uk-UA`)
  - list of saved items
  - quick example phrases

### Project structure

- `main.py` – FastAPI app, HTTP routes and response models
- `database.py` – SQLite access (create, save, find, list, delete items)
- `nlp.py` – intent detection and item/location extraction from Ukrainian text
- `static/index.html` – single‑page UI (HTML + CSS + JS)
- `requirements.txt` – Python dependencies
- `stuff.db` – SQLite database file (created at runtime, **do not commit**)

### Requirements

- Python 3.10+ (recommended)
- pip

### Installation & local run

```bash
cd where-is-my-stuff

# Install dependencies
pip install -r requirements.txt

# Optionally set a family API key (recommended)
export FAMILY_API_KEY="your-secret-family-key"

# Run the server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Open the UI in a browser:

- `http://localhost:8000/`

### Family API key (security)

To prevent strangers on the internet from changing your item locations, all
state‑changing and item‑listing endpoints require a shared **family API key**:

- Environment variable on the server:

  - `FAMILY_API_KEY` – secret string shared only with your family

- The frontend UI:
  - has a “family key” input at the top
  - stores the key in `localStorage`
  - sends it as `X-API-Key: <your_key>` header for:
    - `POST /voice`
    - `GET /items`
    - `DELETE /items/{id}`

If the key is missing or incorrect, the backend responds with `401 Unauthorized`.

### API overview

- `POST /voice`
  - Body: `{ "text": "<Ukrainian sentence>" }`
  - Response:
    - `reply`: text spoken back to the user (Ukrainian)
    - `intent`: `"save" | "query" | "unknown"`
    - `item`, `location` where applicable

- `GET /items`
  - Returns all saved items with their locations and timestamps.

- `DELETE /items/{item_id}`
  - Deletes a single record by ID.

All these endpoints require `X-API-Key` with the correct family key.

### Deployment notes (Render.com example)

Basic Render Web Service settings:

- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port 10000`
- **Environment variable**: set `FAMILY_API_KEY` in the Render dashboard.

You can then share the Render URL with your family; they just need to know the
family key to be able to update item locations.

