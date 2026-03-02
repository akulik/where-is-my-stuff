"""
PostgreSQL (Neon) database module.
Stores and looks up item locations.
"""
import os
from datetime import datetime
from typing import Optional

# Use psycopg2 to connect to PostgreSQL
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_connection():
    """Open a connection to the PostgreSQL database."""
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable is not set!")
    
    # Connect and specify that we want to receive results as dictionary-like objects
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def init_db() -> None:
    """Create items table if it does not exist."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            # PostgreSQL uses SERIAL instead of AUTOINCREMENT 
            # and TIMESTAMP instead of TEXT for dates
            cur.execute("""
                CREATE TABLE IF NOT EXISTS items (
                    id          SERIAL PRIMARY KEY,
                    item        TEXT    NOT NULL,
                    location    TEXT    NOT NULL,
                    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        with conn.cursor() as cur:
            # In PostgreSQL, parameter markers are denoted as %s (not ?)
            cur.execute(
                "SELECT id FROM items WHERE LOWER(item) = %s", (item,)
            )
            existing = cur.fetchone()

            if existing:
                # Update location and timestamp
                cur.execute(
                    "UPDATE items SET location = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                    (location, existing["id"]),
                )
                conn.commit()
                return "updated"
            else:
                # Insert a new record
                cur.execute(
                    "INSERT INTO items (item, location) VALUES (%s, %s)",
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
        with conn.cursor() as cur:
            # 1. Exact match
            cur.execute(
                "SELECT item, location FROM items WHERE LOWER(item) = %s",
                (query,),
            )
            row = cur.fetchone()
            if row:
                return {"item": row["item"], "location": row["location"]}

            # 2. LIKE search (substring search)
            cur.execute(
                "SELECT item, location FROM items WHERE LOWER(item) LIKE %s",
                (f"%{query}%",),
            )
            row = cur.fetchone() # Get the first match if there are multiple
            if row:
                return {"item": row["item"], "location": row["location"]}

            # Reverse LIKE: look for stored item name inside the query
            cur.execute(
                "SELECT item, location FROM items WHERE %s LIKE '%%' || LOWER(item) || '%%'",
                (query,),
            )
            row = cur.fetchone()
            if row:
                return {"item": row["item"], "location": row["location"]}

            # 3. Fuzzy search with thefuzz
            cur.execute("SELECT item, location FROM items")
            all_items = cur.fetchall()

    if not all_items:
        return None

    from thefuzz import fuzz

    best_match = None
    best_score = 0

    for row in all_items:
        stored = row["item"]
        score = fuzz.partial_ratio(query, stored)
        if score > best_score:
            best_score = score
            best_match = {"item": stored, "location": row["location"]}

    if best_score >= 65:
        return best_match

    return None


def get_all_items() -> list[dict]:
    """Return all saved items (for viewing via API)."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, item, location, updated_at FROM items ORDER BY updated_at DESC"
            )
            rows = cur.fetchall()
            
            result = []
            for row in rows:
                # Convert RealDictRow (from psycopg2) into a standard Python dictionary
                row_dict = dict(row)
                # Format the datetime object to a string if necessary
                if isinstance(row_dict["updated_at"], datetime):
                    row_dict["updated_at"] = row_dict["updated_at"].strftime("%Y-%m-%d %H:%M:%S")
                result.append(row_dict)
            return result


def delete_item(item_id: int) -> bool:
    """Delete a record by ID. Return True if a row was actually deleted."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM items WHERE id = %s", (item_id,))
            conn.commit()
            return cur.rowcount > 0