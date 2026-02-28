"""
SQLite database module.
Stores and looks up item locations.
"""
import sqlite3
from datetime import datetime
from typing import Optional

# Database file name
DB_FILE = "stuff.db"


def get_connection() -> sqlite3.Connection:
    """Open a connection to the database."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # return rows as dict-like objects
    return conn


def init_db() -> None:
    """Create items table if it does not exist."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                item        TEXT    NOT NULL,
                location    TEXT    NOT NULL,
                updated_at  TEXT    DEFAULT (datetime('now','localtime'))
            )
        """)
        conn.commit()


def save_item(item: str, location: str) -> str:
    """
    Save or update an item's location.
    If the item already exists — update the location.
    If it is new — insert a record.
    Returns 'updated' or 'created'.
    """
    item = item.strip().lower()
    location = location.strip().lower()

    with get_connection() as conn:
        # Look for exact match (case-insensitive)
        existing = conn.execute(
            "SELECT id FROM items WHERE LOWER(item) = ?", (item,)
        ).fetchone()

        if existing:
            # Update location and timestamp
            conn.execute(
                "UPDATE items SET location = ?, updated_at = ? WHERE id = ?",
                (location, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), existing["id"]),
            )
            conn.commit()
            return "updated"
        else:
            # Insert a new record
            conn.execute(
                "INSERT INTO items (item, location) VALUES (?, ?)",
                (item, location),
            )
            conn.commit()
            return "created"


def find_item(query: str) -> Optional[dict]:
    """
    Look up an item in the database.
    Steps: exact match, then LIKE, then fuzzy search (thefuzz).
    Returns dict {item, location} or None.
    """
    query = query.strip().lower()

    with get_connection() as conn:
        # 1. Exact match
        row = conn.execute(
            "SELECT item, location FROM items WHERE LOWER(item) = ?",
            (query,),
        ).fetchone()
        if row:
            return {"item": row["item"], "location": row["location"]}

        # 2. LIKE search (substring search)
        # Useful when query "ключ" should find "ключі" and vice versa
        rows = conn.execute(
            "SELECT item, location FROM items WHERE LOWER(item) LIKE ?",
            (f"%{query}%",),
        ).fetchall()
        if rows:
            return {"item": rows[0]["item"], "location": rows[0]["location"]}

        # Reverse LIKE: look for stored item name inside the query
        # For example: stored "ключі", query "ключами"
        rows = conn.execute(
            "SELECT item, location FROM items WHERE ? LIKE '%' || LOWER(item) || '%'",
            (query,),
        ).fetchall()
        if rows:
            return {"item": rows[0]["item"], "location": rows[0]["location"]}

        # 3. Fuzzy search with thefuzz
        # Handles different word endings / inflections
        all_items = conn.execute(
            "SELECT item, location FROM items"
        ).fetchall()

    if not all_items:
        return None

    # Import here so startup time is not affected if the library is never used
    from thefuzz import fuzz

    best_match = None
    best_score = 0

    for row in all_items:
        stored = row["item"]
        # partial_ratio works well with substrings (ключ → ключі)
        score = fuzz.partial_ratio(query, stored)
        if score > best_score:
            best_score = score
            best_match = {"item": stored, "location": row["location"]}

    # Minimal match score threshold — 65%
    if best_score >= 65:
        return best_match

    return None


def get_all_items() -> list[dict]:
    """Return all saved items (for viewing via API)."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, item, location, updated_at FROM items ORDER BY updated_at DESC"
        ).fetchall()
        return [dict(row) for row in rows]


def delete_item(item_id: int) -> bool:
    """Delete a record by ID. Return True if something was deleted."""
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
        conn.commit()
        return cursor.rowcount > 0
