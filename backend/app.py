"""
Flask REST API for AI Research Assistant.
Endpoints: /health, /upload, /ask. Serves React frontend and stores conversation history.
"""

import os
import uuid
from pathlib import Path

from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.utils import secure_filename

from config import FlaskConfig, UPLOAD_FOLDER
from pdf_processor import PDFProcessor
from text_chunker import TextChunker
from embeddings_engine import EmbeddingEngine
from summarizer import PaperSummarizer
from research_insights import ResearchInsightsEngine
from qa_engine import QAEngine
from chat_memory import ChatMemory

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.config.from_object(FlaskConfig)
CORS(app, origins=["http://localhost:3000", "http://127.0.0.1:3000"])

UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

# Global state: one active paper per "session" (we use session_id = filename stem or upload id)
pdf_processor = PDFProcessor()
chunker = TextChunker()
embedding_engine = EmbeddingEngine()
summarizer = PaperSummarizer()
insights_engine = ResearchInsightsEngine()
qa_engine = QAEngine(embedding_engine)
chat_memory = ChatMemory()


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in FlaskConfig.ALLOWED_EXTENSIONS


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.route("/health", methods=["GET"])
def health():
    """Check API status."""
    return jsonify({"status": "ok", "message": "AI Research Assistant API is running"})


@app.route("/upload", methods=["POST"])
def upload():
    """
    Upload a research paper PDF. Extracts text, builds FAISS index, returns summary and insights.
    """
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": "Only PDF files are allowed"}), 400

    try:
        filename = secure_filename(file.filename)
        # Use unique name to avoid overwrites
        unique_id = str(uuid.uuid4())[:8]
        base, ext = os.path.splitext(filename)
        save_name = f"{base}_{unique_id}{ext}"
        filepath = UPLOAD_FOLDER / save_name
        file.save(str(filepath))
    except Exception as e:
        return jsonify({"error": f"Failed to save file: {str(e)}"}), 500

    try:
        full_text = pdf_processor.process(filepath)
    except FileNotFoundError:
        return jsonify({"error": "File not found after upload"}), 500
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    if not full_text or len(full_text.strip()) < 100:
        return jsonify({"error": "Could not extract enough text from the PDF"}), 400

    try:
        chunks = chunker.chunk(full_text)
        if not chunks:
            chunks = [full_text[:4000]]
        embedding_engine.create_index(chunks)
    except Exception as e:
        return jsonify({"error": f"Failed to build search index: {str(e)}"}), 500

    try:
        summary_result = summarizer.summarize(full_text)
        abstract = summary_result.get("abstract", "")
        sections = summary_result.get("sections", {})
    except Exception as e:
        abstract = full_text[:800] + "..."
        sections = {}

    try:
        insights = insights_engine.generate_all(full_text)
    except Exception as e:
        insights = {
            "key_contributions": [],
            "limitations": [],
            "future_research": [],
            "research_gaps": [],
            "suggested_titles": [],
            "important_sentences": [],
        }

    session_id = Path(save_name).stem
    chat_memory.clear(session_id)

    return jsonify({
        "session_id": session_id,
        "filename": save_name,
        "summary": {
            "abstract": abstract,
            "sections": sections,
        },
        "key_contributions": insights.get("key_contributions", []),
        "future_research": insights.get("future_research", []),
        "limitations": insights.get("limitations", []),
        "research_gaps": insights.get("research_gaps", []),
        "suggested_titles": insights.get("suggested_titles", []),
        "important_sentences": insights.get("important_sentences", []),
    })


@app.route("/ask", methods=["POST"])
def ask():
    """
    Ask a question about the uploaded paper. Returns AI answer and relevant sections.
    """
    data = request.get_json() or {}
    question = (data.get("question") or "").strip()
    session_id = (data.get("session_id") or "").strip()

    if not question:
        return jsonify({"error": "Missing 'question' in request body"}), 400

    if not embedding_engine.has_index:
        return jsonify({"error": "No paper uploaded yet. Please upload a PDF first."}), 400

    try:
        answer, relevant_chunks = qa_engine.answer(question)
    except Exception as e:
        return jsonify({"error": f"Failed to generate answer: {str(e)}"}), 500

    if session_id:
        chat_memory.add(session_id, question, answer, relevant_sections=relevant_chunks)

    return jsonify({
        "answer": answer,
        "relevant_sections": relevant_chunks[:3],
        "session_id": session_id,
    })


@app.route("/history", methods=["GET"])
def history():
    """Get conversation history for a session."""
    session_id = request.args.get("session_id", "").strip()
    if not session_id:
        return jsonify({"history": []})
    return jsonify({"history": chat_memory.get_history_as_dicts(session_id)})


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
