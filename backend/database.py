import sqlite3
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from config import FlaskConfig

class DBManager:
    """
    Manages SQLite database storage for documents, chat history, and configuration settings.
    Provides persistence without complex setup.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or FlaskConfig.DATABASE_URI
        # Ensure parent directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Initialize SQLite tables for documents, chat logs, and settings."""
        with self.get_connection() as conn:
            # Create documents table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    filepath TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    key_contributions TEXT,
                    limitations TEXT,
                    future_research TEXT,
                    research_gaps TEXT,
                    suggested_titles TEXT,
                    important_sentences TEXT,
                    "references" TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Safe schema migration for existing databases
            try:
                conn.execute('ALTER TABLE documents ADD COLUMN "references" TEXT')
            except sqlite3.OperationalError:
                pass # Already exists

            # Create chat_history table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    sections TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create settings table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            conn.commit()

    # Document APIs
    def save_document(self, doc_id: str, filename: str, filepath: str, data: Dict[str, Any]) -> None:
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO documents (
                    id, filename, filepath, summary, key_contributions, 
                    limitations, future_research, research_gaps, 
                    suggested_titles, important_sentences, "references"
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    doc_id,
                    filename,
                    filepath,
                    json.dumps(data.get("summary", {})),
                    json.dumps(data.get("key_contributions", [])),
                    json.dumps(data.get("limitations", [])),
                    json.dumps(data.get("future_research", [])),
                    json.dumps(data.get("research_gaps", [])),
                    json.dumps(data.get("suggested_titles", [])),
                    json.dumps(data.get("important_sentences", [])),
                    json.dumps(data.get("references", {}))
                )
            )
            conn.commit()

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
            if not row:
                return None
            return {
                "session_id": row["id"],
                "filename": row["filename"],
                "filepath": row["filepath"],
                "summary": json.loads(row["summary"]),
                "key_contributions": json.loads(row["key_contributions"] or "[]"),
                "limitations": json.loads(row["limitations"] or "[]"),
                "future_research": json.loads(row["future_research"] or "[]"),
                "research_gaps": json.loads(row["research_gaps"] or "[]"),
                "suggested_titles": json.loads(row["suggested_titles"] or "[]"),
                "important_sentences": json.loads(row["important_sentences"] or "[]"),
                "references": json.loads(row["references"] or "{}")
            }


    def list_documents(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute("SELECT id, filename, created_at FROM documents ORDER BY created_at DESC").fetchall()
            return [{"id": r["id"], "filename": r["filename"], "created_at": r["created_at"]} for r in rows]

    def delete_document(self, doc_id: str) -> None:
        with self.get_connection() as conn:
            # Get filepath to delete file
            row = conn.execute("SELECT filepath FROM documents WHERE id = ?", (doc_id,)).fetchone()
            if row and os.path.exists(row["filepath"]):
                try:
                    os.remove(row["filepath"])
                except Exception:
                    pass
            conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            conn.execute("DELETE FROM chat_history WHERE session_id = ?", (doc_id,))
            conn.commit()

    # Chat Memory APIs
    def add_chat_msg(self, session_id: str, role: str, content: str, sections: Optional[List[str]] = None) -> None:
        with self.get_connection() as conn:
            conn.execute(
                "INSERT INTO chat_history (session_id, role, content, sections) VALUES (?, ?, ?, ?)",
                (session_id, role, content, json.dumps(sections) if sections else None)
            )
            conn.commit()

    def get_chat_history(self, session_id: str) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT role, content, sections FROM chat_history WHERE session_id = ? ORDER BY id ASC",
                (session_id,)
            ).fetchall()
            history = []
            for r in rows:
                history.append({
                    "role": r["role"],
                    "content": r["content"],
                    "text": r["content"],  # Fallback for old key
                    "sections": json.loads(r["sections"]) if r["sections"] else []
                })
            return history

    def clear_chat_history(self, session_id: str) -> None:
        with self.get_connection() as conn:
            conn.execute("DELETE FROM chat_history WHERE session_id = ?", (session_id,))
            conn.commit()

    # Settings APIs
    def save_setting(self, key: str, value: str) -> None:
        with self.get_connection() as conn:
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
            conn.commit()

    def get_setting(self, key: str, default: str = "") -> str:
        with self.get_connection() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
            return row["value"] if row else default
