"""
API Shopping - Lista de la compra (SQLite backend)
"""

import os
import sqlite3
from datetime import datetime

from flask import Blueprint, current_app, g, jsonify, request

shopping_bp = Blueprint("api_shopping", __name__)

DB_PATH = os.path.join("data", "shopping.db")


def _get_db():
    """Get or create a per-request SQLite connection."""
    if "shopping_db" not in g:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        g.shopping_db = sqlite3.connect(DB_PATH)
        g.shopping_db.row_factory = sqlite3.Row
        g.shopping_db.execute(
            "CREATE TABLE IF NOT EXISTS items ("
            "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "  text TEXT NOT NULL,"
            "  added TEXT NOT NULL"
            ")"
        )
    return g.shopping_db


@shopping_bp.teardown_app_request
def _close_db(exc):
    db = g.pop("shopping_db", None)
    if db is not None:
        db.close()


def _migrate_csv_if_exists():
    """One-time migration: import old CSV data into SQLite."""
    csv_path = os.path.join("data", "shopping.csv")
    if not os.path.exists(csv_path):
        return

    import csv

    db = _get_db()
    count = db.execute("SELECT COUNT(*) FROM items").fetchone()[0]
    if count > 0:
        # DB already has data, skip migration
        return

    try:
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = [(r["text"], r.get("added", datetime.now().isoformat())) for r in reader]
        if rows:
            db.executemany("INSERT INTO items (text, added) VALUES (?, ?)", rows)
            db.commit()
        # Rename old file so migration doesn't re-run
        os.rename(csv_path, csv_path + ".migrated")
        current_app.logger.info(f"Migrated {len(rows)} shopping items from CSV to SQLite")
    except Exception as e:
        current_app.logger.error(f"Error migrating shopping CSV: {e}")


@shopping_bp.route("/api/shopping", methods=["GET", "POST", "DELETE"])
def api_shopping():
    """CRUD para la lista de la compra."""
    db = _get_db()
    _migrate_csv_if_exists()

    if request.method == "GET":
        rows = db.execute("SELECT id, text, added FROM items ORDER BY id").fetchall()
        return jsonify([{"id": r["id"], "text": r["text"], "added": r["added"]} for r in rows])

    elif request.method == "POST":
        text = request.json.get("text", "").strip()
        if not text:
            return jsonify({"error": "text is required"}), 400
        added = datetime.now().isoformat()
        db.execute("INSERT INTO items (text, added) VALUES (?, ?)", (text, added))
        db.commit()
        return jsonify({"text": text, "added": added}), 201

    elif request.method == "DELETE":
        item_id = request.json.get("id")
        index = request.json.get("index")

        if item_id is not None:
            db.execute("DELETE FROM items WHERE id = ?", (item_id,))
        elif index is not None:
            # Backwards-compatible: delete by positional index
            row = db.execute(
                "SELECT id FROM items ORDER BY id LIMIT 1 OFFSET ?", (int(index),)
            ).fetchone()
            if row:
                db.execute("DELETE FROM items WHERE id = ?", (row["id"],))
            else:
                return jsonify({"success": False, "error": "Index out of range"}), 400
        else:
            return jsonify({"error": "id or index required"}), 400

        db.commit()
        return jsonify({"success": True})

    return jsonify({"error": "Method not allowed"}), 405
