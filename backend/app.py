import os
import uuid
import logging
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

from config import FlaskConfig, UPLOAD_FOLDER
from pdf_processor import PDFProcessor
from text_chunker import TextChunker
from embeddings_engine import EmbeddingEngine
from summarizer import PaperSummarizer
from research_insights import ResearchInsightsEngine
from qa_engine import QAEngine
from database import DBManager
from gemini_engine import GeminiEngine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask
app = Flask(__name__)
app.config.from_object(FlaskConfig)

# Enable CORS (support all localhost frontend origins)
CORS(app, origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8000"])

# Ensure directories exist
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

# Initialize database
db = DBManager()

# Global state: local pipeline fallback engines
pdf_processor = PDFProcessor()
chunker = TextChunker()
embedding_engine = EmbeddingEngine()
summarizer = PaperSummarizer()
insights_engine = ResearchInsightsEngine()
qa_engine = QAEngine(embedding_engine)

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in FlaskConfig.ALLOWED_EXTENSIONS

def get_active_gemini_engine() -> GeminiEngine:
    """Helper to instantiate GeminiEngine using either DB saved key or ENV key."""
    saved_key = db.get_setting("gemini_api_key", "").strip()
    key = saved_key if saved_key else os.environ.get("GEMINI_API_KEY", os.environ.get("GOOGLE_API_KEY", ""))
    return GeminiEngine(api_key=key)

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.route("/health", methods=["GET"])
def health():
    """API health status and active configurations."""
    gemini = get_active_gemini_engine()
    return jsonify({
        "status": "ok",
        "message": "Scientia.ai Research Assistant API is running",
        "mode": "advanced (Gemini)" if gemini.is_available else "offline (local fallback)",
        "has_local_models": True
    })

@app.route("/upload", methods=["POST"])
def upload():
    """
    Upload a research paper. Clean text, build FAISS local vector index,
    and analyze paper using Gemini (fast & deep) or Local pipelines.
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
        unique_id = str(uuid.uuid4())[:8]
        base, ext = os.path.splitext(filename)
        save_name = f"{base}_{unique_id}{ext}"
        filepath = UPLOAD_FOLDER / save_name
        file.save(str(filepath))
    except Exception as e:
        logger.error(f"Failed to save file: {e}")
        return jsonify({"error": f"Failed to save file: {str(e)}"}), 500

    # Extract text and references from PDF
    try:
        raw_text = pdf_processor.extract_text(filepath)
        cleaned_raw = pdf_processor._clean_formatting(raw_text)
        ref_map = pdf_processor.extract_references(cleaned_raw)
        full_text = pdf_processor.remove_references_section(cleaned_raw)
    except Exception as e:
        logger.error(f"Failed to extract PDF: {e}")
        return jsonify({"error": f"Failed to process PDF: {str(e)}"}), 400


    if not full_text or len(full_text.strip()) < 100:
        return jsonify({"error": "Could not extract enough text from the PDF"}), 400

    # Build local FAISS search index for QA chunk retrieval
    try:
        chunks = chunker.chunk(full_text)
        if not chunks:
            chunks = [full_text[:4000]]
        embedding_engine.create_index(chunks)
    except Exception as e:
        logger.error(f"Failed to build vector index: {e}")
        return jsonify({"error": f"Failed to build search index: {str(e)}"}), 500

    # Generate insights and summaries (Prefer Gemini, fallback to BART)
    gemini = get_active_gemini_engine()
    session_id = Path(save_name).stem

    if gemini.is_available:
        logger.info("Using advanced Gemini engine for summarization & insights")
        try:
            insights = gemini.generate_summary_and_insights(full_text)
            # Standardize payload structure
            response_payload = {
                "session_id": session_id,
                "filename": filename,
                "summary": {
                    "abstract": insights.get("abstract", ""),
                    "sections": insights.get("sections", {}),
                    "tables": insights.get("tables", []),
                    "equations": insights.get("equations", [])
                },
                "key_contributions": insights.get("key_contributions", []),
                "future_research": insights.get("future_research", []),
                "limitations": insights.get("limitations", []),
                "research_gaps": insights.get("research_gaps", []),
                "suggested_titles": insights.get("suggested_titles", []),
                "important_sentences": insights.get("important_sentences", []),
                "references": ref_map
            }
        except Exception as e:
            logger.error(f"Gemini analysis failed: {e}. Falling back to local BART pipeline.")
            gemini_failed = True
        else:
            gemini_failed = False
    else:
        logger.info("No Gemini API key available. Using local BART pipeline.")
        gemini_failed = True

    # Fallback Local Processing
    if gemini_failed:
        try:
            summary_result = summarizer.summarize(full_text)
            abstract = summary_result.get("abstract", "")
            sections = summary_result.get("sections", {})
        except Exception as e:
            logger.error(f"Local summarizer failed: {e}")
            abstract = full_text[:800] + "..."
            sections = {}

        try:
            local_insights = insights_engine.generate_all(full_text)
        except Exception as e:
            logger.error(f"Local insights failed: {e}")
            local_insights = {}

        response_payload = {
            "session_id": session_id,
            "filename": filename,
            "summary": {
                "abstract": abstract,
                "sections": sections,
                "tables": [],
                "equations": []
            },
            "key_contributions": local_insights.get("key_contributions", []),
            "future_research": local_insights.get("future_research", []),
            "limitations": local_insights.get("limitations", []),
            "research_gaps": local_insights.get("research_gaps", []),
            "suggested_titles": local_insights.get("suggested_titles", []),
            "important_sentences": local_insights.get("important_sentences", []),
            "references": ref_map
        }

    # Save to SQLite database for persistent storage
    try:
        db.save_document(session_id, filename, str(filepath), response_payload)
        db.clear_chat_history(session_id)
    except Exception as e:
        logger.error(f"Failed to save document metadata in DB: {e}")

    return jsonify(response_payload)

@app.route("/ask", methods=["POST"])
def ask():
    """
    Ask a question about the active paper.
    Retrieves local relevant context chunks and passes to Gemini / local LLMs for answer.
    """
    data = request.get_json() or {}
    question = (data.get("question") or "").strip()
    session_id = (data.get("session_id") or "").strip()

    if not question:
        return jsonify({"error": "Missing 'question' in request body"}), 400

    if not session_id:
        return jsonify({"error": "No paper context selected. Please select or upload a document."}), 400

    # Parse potential multiple session IDs
    session_ids = [s.strip() for s in session_id.split(",") if s.strip()]
    
    # Dynamically build a combined FAISS index for multi-document RAG if needed
    if len(session_ids) > 1:
        logger.info(f"Setting up multi-document RAG space for sessions: {session_ids}")
        all_chunks = []
        for s_id in session_ids:
            doc = db.get_document(s_id)
            if doc and os.path.exists(doc["filepath"]):
                try:
                    doc_text = pdf_processor.remove_references_section(pdf_processor._clean_formatting(pdf_processor.extract_text(doc["filepath"])))
                    doc_chunks = chunker.chunk(doc_text)
                    all_chunks.extend(doc_chunks)
                except Exception as e:
                    logger.error(f"Failed to extract text for multi-doc session {s_id}: {e}")
        if all_chunks:
            try:
                embedding_engine.create_index(all_chunks)
            except Exception as e:
                logger.error(f"Failed to create combined FAISS index: {e}")
    else:
        # Single document check - lazy-load if cleared
        if not embedding_engine.has_index:
            doc = db.get_document(session_id)
            if doc and os.path.exists(doc["filepath"]):
                try:
                    full_text = pdf_processor.remove_references_section(pdf_processor._clean_formatting(pdf_processor.extract_text(doc["filepath"])))
                    chunks = chunker.chunk(full_text)
                    embedding_engine.create_index(chunks)
                except Exception as e:
                    logger.error(f"Re-creating FAISS index on query failed: {e}")
                    return jsonify({"error": "No vector search index found for the paper."}), 400
            else:
                return jsonify({"error": "No paper search index found. Please upload a PDF first."}), 400


    try:
        relevant_chunks = qa_engine.get_relevant_chunks(question)
    except Exception as e:
        logger.error(f"Failed to retrieve chunks: {e}")
        relevant_chunks = []

    context = "\n\n".join(relevant_chunks) if relevant_chunks else "No context available."
    history = db.get_chat_history(session_id)

    # Use Gemini or local QA
    gemini = get_active_gemini_engine()
    if gemini.is_available:
        logger.info("Answering using advanced Gemini cloud model")
        try:
            answer = gemini.answer_question(question, context, history)
        except Exception as e:
            logger.error(f"Gemini QA failed: {e}. Falling back to local pipeline.")
            gemini_failed = True
        else:
            gemini_failed = False
    else:
        gemini_failed = True

    # Fallback QA
    if gemini_failed:
        logger.info("Answering using local BART model")
        try:
            answer, _ = qa_engine.answer(question)
        except Exception as e:
            logger.error(f"Local QA failed: {e}")
            answer = "Sorry, failed to generate an answer using local model fallback."

    # Save user/AI exchanges to SQLite
    try:
        db.add_chat_msg(session_id, "user", question)
        db.add_chat_msg(session_id, "assistant", answer, relevant_chunks)
    except Exception as e:
        logger.error(f"Failed to log chat interaction: {e}")

    return jsonify({
        "answer": answer,
        "relevant_sections": relevant_chunks[:3],
        "session_id": session_id
    })

@app.route("/history", methods=["GET"])
def history():
    """Get chat history logs for a session."""
    session_id = request.args.get("session_id", "").strip()
    if not session_id:
        return jsonify({"history": []})
    try:
        history_list = db.get_chat_history(session_id)
        return jsonify({"history": history_list})
    except Exception as e:
        logger.error(f"Failed to load history: {e}")
        return jsonify({"history": []}), 500

# ---------------------------------------------------------------------------
# Dynamic Document Management & API Settings Endpoints
# ---------------------------------------------------------------------------

@app.route("/documents", methods=["GET"])
def get_documents():
    """List all saved research documents."""
    try:
        docs = db.list_documents()
        return jsonify({"documents": docs})
    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        return jsonify({"documents": []}), 500

@app.route("/documents/<doc_id>", methods=["GET", "DELETE"])
def manage_document(doc_id):
    """Get or delete a saved document by its ID."""
    if request.method == "DELETE":
        try:
            db.delete_document(doc_id)
            # If the deleted paper was the active one, clear FAISS index state
            embedding_engine._index = None
            embedding_engine._chunks = []
            return jsonify({"status": "success", "message": f"Document {doc_id} deleted."})
        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            return jsonify({"error": str(e)}), 500
    
    # GET method
    try:
        doc = db.get_document(doc_id)
        if not doc:
            return jsonify({"error": "Document not found"}), 404
        
        # Load local FAISS index for this paper
        if doc and os.path.exists(doc["filepath"]):
            try:
                full_text = pdf_processor.process(doc["filepath"])
                chunks = chunker.chunk(full_text)
                embedding_engine.create_index(chunks)
            except Exception as e:
                logger.error(f"FAISS lazy load failed: {e}")
        
        return jsonify(doc)
    except Exception as e:
        logger.error(f"Failed to fetch document: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/settings", methods=["GET", "POST"])
def manage_settings():
    """Get or update dynamically configured settings."""
    if request.method == "POST":
        data = request.get_json() or {}
        gemini_key = data.get("gemini_api_key", "").strip()
        try:
            db.save_setting("gemini_api_key", gemini_key)
            return jsonify({"status": "success", "message": "API settings updated successfully."})
        except Exception as e:
            logger.error(f"Failed to save setting: {e}")
            return jsonify({"error": str(e)}), 500

    # GET method
    try:
        saved_key = db.get_setting("gemini_api_key", "")
        # Mask the key for security before returning
        masked = ""
        if saved_key:
            masked = f"{saved_key[:6]}...{saved_key[-4:]}" if len(saved_key) > 10 else "********"
        
        return jsonify({
            "has_key": bool(saved_key or os.environ.get("GEMINI_API_KEY")),
            "masked_key": masked
        })
    except Exception as e:
        logger.error(f"Failed to load settings: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/citation", methods=["GET"])
def get_citation():
    """
    Lookup a specific citation number in a session, and fetch its scholarly abstract
    and metric benchmarks from OpenAlex API in the background.
    """
    session_id = request.args.get("session_id", "").strip()
    ref_num = request.args.get("ref_num", "").strip()

    if not session_id or not ref_num:
        return jsonify({"error": "Missing session_id or ref_num"}), 400

    try:
        doc = db.get_document(session_id)
        if not doc:
            return jsonify({"error": "Document not found"}), 404
        
        ref_map = doc.get("references", {})
        citation_text = ref_map.get(ref_num)
        if not citation_text:
            return jsonify({"error": f"Citation [{ref_num}] not found in this document."}), 404

        # Query scholarly details from OpenAlex
        from scholarly_service import ScholarlyService
        scholarly_details = ScholarlyService.search_paper_by_title(citation_text)
        
        if scholarly_details:
            return jsonify({
                "ref_num": ref_num,
                "raw_text": citation_text,
                "scholarly_found": True,
                **scholarly_details
            })
        return jsonify({
            "ref_num": ref_num,
            "raw_text": citation_text,
            "scholarly_found": False,
            "title": citation_text[:120] + "..." if len(citation_text) > 120 else citation_text,
            "abstract": "Scholarly details could not be retrieved from the open-access API registry."
        })
    except Exception as e:
        logger.error(f"Failed to fetch citation details: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/synthesis", methods=["POST"])
def synthesize_documents():
    """
    Accepts a list of document IDs, fetches their metadata from SQLite,
    and runs a comparative analysis using Gemini to compile a comparative matrix.
    """
    data = request.get_json() or {}
    session_ids = data.get("session_ids", [])
    
    if not session_ids or not isinstance(session_ids, list):
        return jsonify({"error": "Missing or invalid 'session_ids' array in request body"}), 400

    docs = []
    headers = {}
    for s_id in session_ids:
        doc = db.get_document(s_id)
        if not doc:
            return jsonify({"error": f"Document {s_id} not found."}), 404
        docs.append(doc)
        headers[s_id] = doc["filename"]

    # Build prompt for Gemini comparing the papers
    gemini = get_active_gemini_engine()
    if not gemini.is_available:
        return jsonify({"error": "Gemini API key is not configured. Please enter one in Settings."}), 400

    import json
    # Compile document details to send to LLM
    doc_inputs = []
    for d in docs:
        doc_inputs.append({
            "session_id": d["session_id"],
            "filename": d["filename"],
            "abstract": d["summary"].get("abstract", ""),
            "contributions": d.get("key_contributions", []),
            "limitations": d.get("limitations", [])
        })

    prompt = f"""You are an elite AI Research Principal. Your task is to perform a detailed comparative synthesis of the following research papers.
    Analyze their methodologies, technical parameter scopes, datasets, and performance benchmarks side-by-side.

    Generate your response in EXACTLY the following JSON format:
    {{
        "comparisons": [
            {{
                "attribute": "Core Methodology",
                "explanation": "Brief overview comparing the technical approaches used.",
                "values": {{
                    "session_id_1": "Brief methodology summary for paper 1",
                    "session_id_2": "Brief methodology summary for paper 2"
                }}
            }},
            {{
                "attribute": "Datasets Evaluated",
                "explanation": "Comparison of datasets, sizes, and collection methods.",
                "values": {{
                    "session_id_1": "Datasets used in paper 1",
                    "session_id_2": "Datasets used in paper 2"
                }}
            }},
            {{
                "attribute": "Performance Benchmarks",
                "explanation": "Comparison of accuracy, F1, latency, or SOTA metrics.",
                "values": {{
                    "session_id_1": "Benchmark results for paper 1",
                    "session_id_2": "Benchmark results for paper 2"
                }}
            }},
            {{
                "attribute": "Parameters & Architectural Scale",
                "explanation": "Comparison of model size, parameters, layers, or compute details.",
                "values": {{
                    "session_id_1": "Architectural size of paper 1",
                    "session_id_2": "Architectural size of paper 2"
                }}
            }}
        ]
    }}

    Do NOT include any markdown packaging. Return ONLY the raw valid JSON string.

    Papers to Compare:
    {json.dumps(doc_inputs, indent=2)}
    """

    try:
        import google.generativeai as genai
        model = genai.GenerativeModel(gemini.model_name)
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        
        cleaned = response.text.strip()
        # Clean potential markdown wrapping
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()

        result = json.loads(cleaned)
        return jsonify({
            "headers": headers,
            "comparisons": result.get("comparisons", [])
        })
    except Exception as e:
        logger.error(f"Comparative synthesis failed: {e}")
        return jsonify({"error": f"Synthesis compilation failed: {str(e)}"}), 500

@app.route("/podcast", methods=["POST"])
def create_podcast():
    """Generate a streamable audio overview for a research paper."""
    data = request.get_json() or {}
    session_id = data.get("session_id", "").strip()

    if not session_id:
        return jsonify({"error": "Missing session_id"}), 400

    doc = db.get_document(session_id)
    if not doc:
        return jsonify({"error": "Document not found"}), 404

    gemini = get_active_gemini_engine()
    if not gemini.is_available:
        return jsonify({"error": "Gemini API key is not configured. Please add one in Settings."}), 400

    try:
        # Re-extract text from PDF to get full details for TTS briefing
        raw_text = pdf_processor.extract_text(doc["filepath"])
        cleaned_raw = pdf_processor._clean_formatting(raw_text)
        full_text = pdf_processor.remove_references_section(cleaned_raw)

        from podcast_service import PodcastService
        audio_path = PodcastService.generate_audio_overview(
            session_id=session_id,
            doc_title=doc["filename"],
            full_text=full_text,
            gemini=gemini
        )
        
        if audio_path:
            return jsonify({
                "status": "success",
                "url": f"/podcast/{session_id}.mp3"
            })
        else:
            return jsonify({"error": "Failed to compile audio overview"}), 500
    except Exception as e:
        logger.error(f"Failed to generate podcast: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/podcast/<session_id>.mp3", methods=["GET"])
def stream_podcast(session_id):
    """Serve the synthesized podcast MP3 file directly."""
    filename = f"{session_id}_podcast.mp3"
    return send_from_directory(UPLOAD_FOLDER, filename, mimetype="audio/mpeg")

@app.route("/synthesize_code", methods=["POST"])
def synthesize_code():
    """Analyze document methodology and synthesize PyTorch code skeleton."""
    data = request.get_json() or {}
    session_id = data.get("session_id", "").strip()

    if not session_id:
        return jsonify({"error": "Missing session_id"}), 400

    doc = db.get_document(session_id)
    if not doc:
        return jsonify({"error": "Document not found"}), 404

    gemini = get_active_gemini_engine()
    if not gemini.is_available:
        return jsonify({"error": "Gemini API key is not configured. Please add one in Settings."}), 400

    try:
        raw_text = pdf_processor.extract_text(doc["filepath"])
        cleaned_raw = pdf_processor._clean_formatting(raw_text)
        full_text = pdf_processor.remove_references_section(cleaned_raw)

        prompt = f"""You are a senior Machine Learning Architect. Analyze the methodology, neural network layers, parameters, algorithms, and technical processes described in the following research paper context.
        
        Generate a fully structured, production-grade, highly readable PyTorch class structure scaffold representing this paper's core methodology.
        Include:
        - Precise PyTorch custom module classes (e.g. layers, attention blocks, loss functions).
        - Detailed forward pass calculations.
        - Boilerplate setup for the optimizer, training loops, and a dataloader structure.
        - Heavy explanatory inline comments explaining how specific blocks of code map to specific equations or methodologies in the paper.
        
        Do NOT write simple pseudocode; provide actual syntactically-valid PyTorch code using proper imports and typical configurations.
        Return ONLY the raw executable Python code. Do not wrap it in markdown block tags (like ```python ... ```) or conversational preamble.
        
        Research Paper context:
        {full_text[:200000]}
        """

        import google.generativeai as genai
        model = genai.GenerativeModel(gemini.model_name)
        response = model.generate_content(prompt)
        
        code = response.text.strip()
        # Clean potential markdown wrapping
        if code.startswith("```"):
            lines = code.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            code = "\n".join(lines).strip()
            if code.startswith("python"):
                code = code[6:].strip()

        return jsonify({
            "status": "success",
            "code": code
        })
    except Exception as e:
        logger.error(f"Failed to synthesize code: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)



