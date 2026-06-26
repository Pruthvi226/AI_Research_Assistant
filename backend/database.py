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
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Initialize SQLite tables for documents, chunks, chats, logs, outputs, and settings."""
        with self.get_connection() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            # Create documents table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    filepath TEXT NOT NULL,
                    text_cache TEXT,
                    chunks TEXT,
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
            for column_sql in (
                'ALTER TABLE documents ADD COLUMN "references" TEXT',
                "ALTER TABLE documents ADD COLUMN text_cache TEXT",
                "ALTER TABLE documents ADD COLUMN chunks TEXT",
            ):
                try:
                    conn.execute(column_sql)
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

            conn.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(document_id) REFERENCES documents(id)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS chats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    user_query TEXT NOT NULL,
                    selected_agent TEXT NOT NULL,
                    intent TEXT,
                    response TEXT NOT NULL,
                    sources TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    selected_agent TEXT NOT NULL,
                    intent TEXT,
                    query TEXT,
                    response_preview TEXT,
                    status TEXT DEFAULT 'success',
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS generated_outputs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    output_type TEXT NOT NULL,
                    title TEXT,
                    content TEXT,
                    file_path TEXT,
                    metadata TEXT,
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
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_history_session ON chat_history(session_id, id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id, chunk_index)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chats_session ON chats(session_id, id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_logs_created_at ON agent_logs(created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_generated_outputs_session ON generated_outputs(session_id, id)")
            conn.commit()

    # Document APIs
    def save_document(
        self,
        doc_id: str,
        filename: str,
        filepath: str,
        data: Dict[str, Any],
        full_text: str = "",
        chunks: Optional[List[str]] = None,
        chunk_records: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        chunk_records = chunk_records or [
            {"content": chunk, "metadata": {"chars": len(chunk)}} for chunk in (chunks or [])
        ]
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO documents (
                    id, filename, filepath, text_cache, chunks, summary, key_contributions,
                    limitations, future_research, research_gaps,
                    suggested_titles, important_sentences, "references"
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    doc_id,
                    filename,
                    filepath,
                    full_text,
                    json.dumps(chunks or []),
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
            conn.execute("DELETE FROM chunks WHERE document_id = ?", (doc_id,))
            for index, record in enumerate(chunk_records):
                chunk = record.get("content", "")
                if not chunk:
                    continue
                metadata = record.get("metadata", {})
                metadata.setdefault("chars", len(chunk))
                metadata.setdefault("chunk_index", index)
                conn.execute(
                    """
                    INSERT INTO chunks (document_id, chunk_index, content, metadata)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        doc_id,
                        index,
                        chunk,
                        json.dumps({"filename": filename, **metadata}),
                    ),
                )
            conn.commit()

    def update_document_cache(
        self,
        doc_id: str,
        full_text: str,
        chunks: List[str],
        chunk_records: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        chunk_records = chunk_records or [
            {"content": chunk, "metadata": {"chars": len(chunk)}} for chunk in chunks
        ]
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE documents SET text_cache = ?, chunks = ? WHERE id = ?",
                (full_text, json.dumps(chunks), doc_id),
            )
            conn.execute("DELETE FROM chunks WHERE document_id = ?", (doc_id,))
            for index, record in enumerate(chunk_records):
                chunk = record.get("content", "")
                metadata = record.get("metadata", {})
                metadata.setdefault("chars", len(chunk))
                metadata.setdefault("chunk_index", index)
                conn.execute(
                    "INSERT INTO chunks (document_id, chunk_index, content, metadata) VALUES (?, ?, ?, ?)",
                    (doc_id, index, chunk, json.dumps(metadata)),
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

    def get_document_content(self, doc_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT filepath, text_cache, chunks FROM documents WHERE id = ?",
                (doc_id,),
            ).fetchone()
            if not row:
                return None
            chunks = []
            if row["chunks"]:
                try:
                    chunks = json.loads(row["chunks"])
                except json.JSONDecodeError:
                    chunks = []
            chunk_records = self.get_chunks_for_document(doc_id)
            return {
                "filepath": row["filepath"],
                "text_cache": row["text_cache"] or "",
                "chunks": chunks,
                "chunk_records": chunk_records,
            }

    def get_chunks_for_document(self, doc_id: str) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT chunk_index, content, metadata
                FROM chunks
                WHERE document_id = ?
                ORDER BY chunk_index ASC
                """,
                (doc_id,),
            ).fetchall()
            records = []
            for row in rows:
                try:
                    metadata = json.loads(row["metadata"] or "{}")
                except json.JSONDecodeError:
                    metadata = {}
                records.append({
                    "chunk_index": row["chunk_index"],
                    "content": row["content"],
                    "metadata": metadata,
                })
            return records

    def list_documents(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT d.id, d.filename, d.created_at, COUNT(c.id) AS chunk_count
                FROM documents d
                LEFT JOIN chunks c ON c.document_id = d.id
                GROUP BY d.id, d.filename, d.created_at
                ORDER BY d.created_at DESC
            """).fetchall()
            return [
                {
                    "id": r["id"],
                    "filename": r["filename"],
                    "created_at": r["created_at"],
                    "chunk_count": r["chunk_count"],
                }
                for r in rows
            ]

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
            conn.execute("DELETE FROM chunks WHERE document_id = ?", (doc_id,))
            conn.execute("DELETE FROM chat_history WHERE session_id = ?", (doc_id,))
            conn.execute("DELETE FROM chats WHERE session_id = ?", (doc_id,))
            conn.execute("DELETE FROM generated_outputs WHERE session_id = ?", (doc_id,))
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
            conn.execute("DELETE FROM chats WHERE session_id = ?", (session_id,))
            conn.commit()

    def log_chat(
        self,
        session_id: str,
        user_query: str,
        selected_agent: str,
        response: str,
        intent: str = "",
        sources: Optional[List[str]] = None,
    ) -> None:
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO chats (session_id, user_query, selected_agent, intent, response, sources)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    user_query,
                    selected_agent,
                    intent,
                    response,
                    json.dumps(sources or []),
                ),
            )
            conn.commit()

    def log_agent(
        self,
        selected_agent: str,
        intent: str,
        query: str,
        response: str,
        status: str = "success",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        preview = (response or "")[:600]
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO agent_logs (selected_agent, intent, query, response_preview, status, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    selected_agent,
                    intent,
                    query,
                    preview,
                    status,
                    json.dumps(metadata or {}),
                ),
            )
            conn.commit()

    def save_generated_output(
        self,
        session_id: str,
        output_type: str,
        title: str,
        content: str = "",
        file_path: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        with self.get_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO generated_outputs (session_id, output_type, title, content, file_path, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    output_type,
                    title,
                    content,
                    file_path,
                    json.dumps(metadata or {}),
                ),
            )
            conn.commit()
            return int(cur.lastrowid)

    def list_agent_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, selected_agent, intent, query, response_preview, status, metadata, created_at
                FROM agent_logs
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [
                {
                    "id": r["id"],
                    "selected_agent": r["selected_agent"],
                    "intent": r["intent"],
                    "query": r["query"],
                    "response_preview": r["response_preview"],
                    "status": r["status"],
                    "metadata": json.loads(r["metadata"] or "{}"),
                    "created_at": r["created_at"],
                }
                for r in rows
            ]

    def list_generated_outputs(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, session_id, output_type, title, content, file_path, metadata, created_at
                FROM generated_outputs
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [
                {
                    "id": r["id"],
                    "session_id": r["session_id"],
                    "output_type": r["output_type"],
                    "title": r["title"],
                    "content": r["content"],
                    "file_path": r["file_path"],
                    "metadata": json.loads(r["metadata"] or "{}"),
                    "created_at": r["created_at"],
                }
                for r in rows
            ]

    def get_generated_output(self, output_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute(
                """
                SELECT id, session_id, output_type, title, content, file_path, metadata, created_at
                FROM generated_outputs
                WHERE id = ?
                """,
                (output_id,),
            ).fetchone()
            if not row:
                return None
            return {
                "id": row["id"],
                "session_id": row["session_id"],
                "output_type": row["output_type"],
                "title": row["title"],
                "content": row["content"],
                "file_path": row["file_path"],
                "metadata": json.loads(row["metadata"] or "{}"),
                "created_at": row["created_at"],
            }

    # Settings APIs
    def save_setting(self, key: str, value: str) -> None:
        with self.get_connection() as conn:
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
            conn.commit()

    def get_setting(self, key: str, default: str = "") -> str:
        with self.get_connection() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
            return row["value"] if row else default