import os
import uuid
import logging
import time
import json
import hmac
from pathlib import Path
from flask import Flask, jsonify, request, send_file, send_from_directory, g
from flask_cors import CORS
from werkzeug.exceptions import HTTPException
from werkzeug.utils import secure_filename

from config import (
    FlaskConfig,
    UPLOAD_FOLDER,
    AUDIO_FOLDER,
    GENERATED_CODE_FOLDER,
    GENERATED_MARKDOWN_FOLDER,
    validate_runtime_environment,
)
from pdf_processor import PDFProcessor
from text_chunker import TextChunker
from embeddings_engine import EmbeddingEngine
from summarizer import PaperSummarizer
from research_insights import ResearchInsightsEngine
from qa_engine import QAEngine
from database import DBManager
from gemini_engine import GeminiEngine
from scholarly_service import ScholarlyService
from agents import (
    OrchestratorAgent,
    ResearchPaperAgent,
    RAGRetrievalAgent,
    MathEquationAgent,
    CodeGenerationAgent,
    CitationAgent,
    GitHubRepoMatcherAgent,
    PodcastAgent,
)
from services.llm_service import LLMService
from services.ocr_service import OCRService
from services.audio_service import AudioService
from services.github_service import GitHubService
from services.system_health_service import SystemHealthService
from services.job_service import JobManager, JobQueueFull
from routes.chat_routes import register_chat_routes
from routes.upload_routes import register_upload_routes
from routes.equation_routes import register_equation_routes
from routes.code_routes import register_code_routes
from routes.citation_routes import register_citation_routes
from routes.github_routes import register_github_routes
from routes.podcast_routes import register_podcast_routes
from utils.validators import IMAGE_EXTENSIONS, validate_extension
from utils.api import SlidingWindowRateLimiter, api_error
from utils.artifacts import write_text_artifact

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask
app = Flask(__name__)
app.config.from_object(FlaskConfig)

# Enable CORS (support all localhost frontend origins)
CORS(app, origins=FlaskConfig.CORS_ORIGINS)

# Ensure directories exist
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
GENERATED_CODE_FOLDER.mkdir(parents=True, exist_ok=True)
GENERATED_MARKDOWN_FOLDER.mkdir(parents=True, exist_ok=True)

# Initialize database
db = DBManager()
_gemini_cache = {"key": None, "engine": None}
_active_index_key = None

# Global state: local pipeline fallback engines
pdf_processor = PDFProcessor()
chunker = TextChunker()
embedding_engine = EmbeddingEngine()
summarizer = PaperSummarizer()
insights_engine = ResearchInsightsEngine()
qa_engine = QAEngine(embedding_engine)
job_manager = JobManager(
    max_workers=FlaskConfig.JOB_WORKERS,
    max_retained_jobs=FlaskConfig.JOB_RETENTION_LIMIT,
    max_in_flight=FlaskConfig.JOB_MAX_IN_FLIGHT,
)
rate_limiter = SlidingWindowRateLimiter(
    limit=FlaskConfig.RATE_LIMIT_PER_MINUTE,
    window_seconds=FlaskConfig.RATE_LIMIT_WINDOW_SECONDS,
)

for env_warning in validate_runtime_environment():
    logger.warning(env_warning)


SENSITIVE_EXACT_PATHS = {
    "/settings",
    "/api/settings",
    "/api/agent-logs",
}
SENSITIVE_PREFIXES = (
    "/api/generated-outputs",
    "/api/jobs",
    "/api/generated-audio",
)


def sensitive_route_requires_admin() -> bool:
    path = request.path.rstrip("/") or "/"
    if path in SENSITIVE_EXACT_PATHS:
        return True
    if request.method == "GET" and path.startswith("/api/jobs/"):
        return False
    if any(path.startswith(prefix) for prefix in SENSITIVE_PREFIXES):
        return True
    if request.method == "DELETE" and (path.startswith("/documents/") or path.startswith("/api/documents/")):
        return True
    if path.startswith("/api/documents/") and path.endswith("/export/markdown"):
        return True
    return False


def provided_admin_key() -> str:
    return (
        request.headers.get("X-Admin-Key")
        or request.cookies.get("scientia_admin")
        or request.args.get("admin_key")
        or ""
    ).strip()



@app.before_request
def start_request_context():
    g.request_id = request.headers.get(FlaskConfig.REQUEST_ID_HEADER) or str(uuid.uuid4())
    g.request_started_at = time.perf_counter()


@app.before_request
def enforce_admin_api_auth():
    if not FlaskConfig.REQUIRE_ADMIN_AUTH or not sensitive_route_requires_admin():
        return None
    expected = FlaskConfig.ADMIN_API_KEY
    if not expected:
        return api_error("Admin API protection is enabled but ADMIN_API_KEY is not configured.", 503, "admin_auth_not_configured")
    if not hmac.compare_digest(provided_admin_key(), expected):
        return api_error("Admin credentials are required for this endpoint.", 401, "admin_auth_required")
    return None


@app.before_request
def enforce_api_rate_limit():
    if request.path.startswith("/api/") and request.path not in {"/api/health", "/api/system/health", "/api/system/metrics", "/api/system/readiness"}:
        key = request.headers.get("X-Forwarded-For", request.remote_addr or "local")
        key = key.split(",", 1)[0].strip()
        if not rate_limiter.check(key):
            return api_error("Too many requests. Please wait a moment and retry.", 429, "rate_limited")


@app.after_request
def attach_operational_headers(response):
    if FlaskConfig.SECURITY_HEADERS_ENABLED:
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: blob:; "
            "media-src 'self' blob:; "
            "connect-src 'self' http://localhost:5000 http://127.0.0.1:5000; "
            "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
        if FlaskConfig.ENVIRONMENT.lower() == "production":
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    request_id = getattr(g, "request_id", "")
    if request_id:
        response.headers[FlaskConfig.REQUEST_ID_HEADER] = request_id
    started_at = getattr(g, "request_started_at", None)
    if started_at is not None:
        response.headers["X-Response-Time-ms"] = str(round((time.perf_counter() - started_at) * 1000, 2))
    return response


@app.errorhandler(HTTPException)
def handle_http_exception(exc):
    return api_error(
        exc.description or exc.name,
        exc.code or 500,
        exc.name.lower().replace(" ", "_"),
        {"request_id": getattr(g, "request_id", "")},
    )


@app.errorhandler(Exception)
def handle_unexpected_exception(exc):
    logger.exception("Unhandled request failure", extra={"request_id": getattr(g, "request_id", "")})
    return api_error(
        "Internal server error",
        500,
        "internal_server_error",
        {"request_id": getattr(g, "request_id", "")},
    )

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in FlaskConfig.ALLOWED_EXTENSIONS

def get_active_gemini_engine() -> GeminiEngine:
    """Helper to instantiate GeminiEngine using either DB saved key or ENV key."""
    saved_key = db.get_setting("gemini_api_key", "").strip()
    key = saved_key if saved_key else os.environ.get("GEMINI_API_KEY", os.environ.get("GOOGLE_API_KEY", ""))
    if _gemini_cache["engine"] is None or _gemini_cache["key"] != key:
        _gemini_cache["key"] = key
        _gemini_cache["engine"] = GeminiEngine(api_key=key)
    return _gemini_cache["engine"]

def invalidate_gemini_cache() -> None:
    _gemini_cache["key"] = None
    _gemini_cache["engine"] = None

def build_chunks(full_text: str) -> list:
    chunks = chunker.chunk(full_text)
    return chunks or [full_text[:4000]]

def label_chunk(filename: str, page: int, chunk_index: int, content: str) -> str:
    return f"[Source {chunk_index + 1} | {filename} | page {page} | chunk {chunk_index + 1}]\n{content.strip()}"

def build_page_chunk_records(filepath: str | Path, filename: str) -> tuple:
    pages = pdf_processor.extract_pages(filepath)
    cleaned_text = "\n\n".join(page["text"] for page in pages)
    ref_map = pdf_processor.extract_references(cleaned_text)
    full_text = pdf_processor.remove_references_section(cleaned_text)
    records = []
    source_idx = 0
    for page in pages:
        page_chunks = build_chunks(page["text"])
        for page_chunk_idx, page_chunk in enumerate(page_chunks):
            if not page_chunk.strip():
                continue
            labeled = label_chunk(filename, page["page"], source_idx, page_chunk)
            records.append({
                "content": labeled,
                "metadata": {
                    "filename": filename,
                    "page": page["page"],
                    "page_chunk_index": page_chunk_idx,
                    "chunk_index": source_idx,
                    "source_label": f"Source {source_idx + 1}",
                },
            })
            source_idx += 1
    chunks = [record["content"] for record in records] or build_chunks(full_text)
    if not records:
        records = [
            {
                "content": chunk,
                "metadata": {
                    "filename": filename,
                    "page": 1,
                    "chunk_index": idx,
                    "source_label": f"Source {idx + 1}",
                },
            }
            for idx, chunk in enumerate(chunks)
        ]
    return full_text, ref_map, chunks, records

def extract_document_text(filepath: str | Path) -> tuple:
    raw_text = pdf_processor.extract_text(filepath)
    cleaned_raw = pdf_processor._clean_formatting(raw_text)
    ref_map = pdf_processor.extract_references(cleaned_raw)
    full_text = pdf_processor.remove_references_section(cleaned_raw)
    return full_text, ref_map

def load_document_text_and_chunks(session_id: str) -> tuple:
    cached = db.get_document_content(session_id)
    if not cached:
        raise ValueError(f"Document {session_id} not found.")

    full_text = cached.get("text_cache") or ""
    chunks = cached.get("chunks") or []
    filepath = cached.get("filepath")

    if full_text and chunks:
        return full_text, chunks

    if not filepath or not os.path.exists(filepath):
        raise ValueError(f"Document file for {session_id} is missing.")

    doc = db.get_document(session_id) or {}
    full_text, _, chunks, chunk_records = build_page_chunk_records(filepath, doc.get("filename", Path(filepath).name))
    db.update_document_cache(session_id, full_text, chunks, chunk_records=chunk_records)
    return full_text, chunks

def ensure_search_index(session_ids: list) -> int:
    """Create a reusable index for one or more selected documents."""
    global _active_index_key
    index_key = ",".join(session_ids)
    if _active_index_key == index_key and embedding_engine.has_index:
        return len(embedding_engine._chunks)

    if len(session_ids) == 1 and embedding_engine.load_index(session_ids[0]):
        _active_index_key = index_key
        return len(embedding_engine._chunks)

    all_chunks = []
    for s_id in session_ids:
        _, doc_chunks = load_document_text_and_chunks(s_id)
        all_chunks.extend(doc_chunks)

    if not all_chunks:
        raise ValueError("No searchable content found for the selected document(s).")

    embedding_engine.create_index(all_chunks)
    if len(session_ids) == 1:
        embedding_engine.save_index(session_ids[0])
    _active_index_key = index_key
    return len(all_chunks)

def bounded_context(chunks: list) -> str:
    context_parts = []
    total = 0
    for chunk in chunks:
        remaining = FlaskConfig.MAX_QA_CONTEXT_CHARS - total
        if remaining <= 0:
            break
        context_parts.append(chunk[:remaining])
        total += len(context_parts[-1])
    return "\n\n".join(context_parts) if context_parts else "No context available."


def artifact_filename(prefix: str, session_id: str, filename: str) -> str:
    stem = Path(filename or "artifact").stem
    suffix = Path(filename or "").suffix or ".txt"
    safe_session = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in (session_id or "general"))
    safe_stem = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in stem)[:80] or "artifact"
    return f"{prefix}_{safe_session}_{safe_stem}_{str(uuid.uuid4())[:8]}{suffix}"


def build_markdown_report(doc: dict) -> str:
    summary = doc.get("summary", {}) or {}
    lines = [
        f"# {doc.get('filename', 'Research Paper')}",
        "",
        f"- Session ID: {doc.get('session_id', '')}",
        f"- Exported: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
    ]

    if summary.get("abstract"):
        lines.extend(["## Abstract", "", summary["abstract"], ""])

    sections = summary.get("sections") or {}
    if sections:
        lines.extend(["## Section Summaries", ""])
        for title, text in sections.items():
            lines.extend([f"### {title}", "", str(text), ""])

    grouped_lists = [
        ("Key Contributions", doc.get("key_contributions") or []),
        ("Limitations", doc.get("limitations") or []),
        ("Future Research", doc.get("future_research") or []),
        ("Research Gaps", doc.get("research_gaps") or []),
        ("Suggested Titles", doc.get("suggested_titles") or []),
        ("Important Sentences", doc.get("important_sentences") or []),
    ]
    for heading, items in grouped_lists:
        if not items:
            continue
        lines.extend([f"## {heading}", ""])
        lines.extend([f"- {item}" for item in items])
        lines.append("")

    references = doc.get("references") or {}
    if references:
        lines.extend(["## References", ""])
        for ref_num, citation in references.items():
            lines.append(f"- [{ref_num}] {citation}")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def process_saved_pdf(filepath: Path, filename: str, save_name: str, job_id: str | None = None) -> dict:
    """Process an already-saved PDF and return the normal upload payload."""
    global _active_index_key
    started_at = time.perf_counter()
    timings = {}
    session_id = Path(save_name).stem

    if job_id:
        job_manager.update(job_id, progress=10, message="Extracting PDF text and page-aware chunks")

    full_text, ref_map, chunks, chunk_records = build_page_chunk_records(filepath, filename)
    timings["extract_ms"] = round((time.perf_counter() - started_at) * 1000)
    if not full_text or len(full_text.strip()) < 100:
        raise ValueError("Could not extract enough text from the PDF")

    if job_id:
        job_manager.update(job_id, progress=35, message="Building retrieval index")

    index_started = time.perf_counter()
    embedding_engine.create_index(chunks)
    index_path = embedding_engine.save_index(session_id, metadata=[record.get("metadata", {}) for record in chunk_records])
    _active_index_key = session_id
    timings["index_ms"] = round((time.perf_counter() - index_started) * 1000)

    if job_id:
        job_manager.update(job_id, progress=55, message="Analyzing research paper")

    gemini = get_active_gemini_engine()
    analysis_mode = "gemini" if gemini.is_available else "local_extractive"
    analysis_started = time.perf_counter()

    if gemini.is_available:
        try:
            insights = gemini.generate_summary_and_insights(full_text[:FlaskConfig.MAX_ANALYSIS_CHARS])
            response_payload = {
                "session_id": session_id,
                "filename": filename,
                "summary": {
                    "abstract": insights.get("abstract", ""),
                    "sections": insights.get("sections", {}),
                    "tables": insights.get("tables", []),
                    "equations": insights.get("equations", []),
                },
                "key_contributions": insights.get("key_contributions", []),
                "future_research": insights.get("future_research", []),
                "limitations": insights.get("limitations", []),
                "research_gaps": insights.get("research_gaps", []),
                "suggested_titles": insights.get("suggested_titles", []),
                "important_sentences": insights.get("important_sentences", []),
                "references": ref_map,
            }
            gemini_failed = False
        except Exception as e:
            logger.error(f"Gemini analysis failed: {e}. Falling back to local extractive pipeline.")
            gemini_failed = True
            analysis_mode = "local_extractive_after_gemini_error"
    else:
        gemini_failed = True

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
                "equations": [],
            },
            "key_contributions": local_insights.get("key_contributions", []),
            "future_research": local_insights.get("future_research", []),
            "limitations": local_insights.get("limitations", []),
            "research_gaps": local_insights.get("research_gaps", []),
            "suggested_titles": local_insights.get("suggested_titles", []),
            "important_sentences": local_insights.get("important_sentences", []),
            "references": ref_map,
        }

    timings["analysis_ms"] = round((time.perf_counter() - analysis_started) * 1000)
    response_payload["performance"] = {
        "mode": analysis_mode,
        "retrieval": "semantic" if embedding_engine.use_semantic else "lexical",
        "chunks": len(chunks),
        "total_ms": round((time.perf_counter() - started_at) * 1000),
        "timings": timings,
        "index_path": index_path,
    }

    if job_id:
        job_manager.update(job_id, progress=80, message="Running Research Paper Agent")

    try:
        paper_agent_result = research_agent.run(
            query="summarize this paper",
            document_text=full_text[:FlaskConfig.MAX_ANALYSIS_CHARS],
            filename=filename,
            summary=response_payload.get("summary", {}),
        )
        response_payload["selected_agent"] = paper_agent_result["selected_agent"]
        response_payload["intent"] = paper_agent_result["intent"]
        response_payload["agent_analysis"] = paper_agent_result.get("artifacts", {}).get("analysis", {})
        db.log_agent(
            selected_agent=paper_agent_result["selected_agent"],
            intent=paper_agent_result["intent"],
            query=f"Uploaded PDF: {filename}",
            response=paper_agent_result["response"],
            metadata={"session_id": session_id, "filename": filename, "duration_ms": response_payload["performance"]["total_ms"]},
        )
    except Exception as e:
        logger.error(f"Research Paper Agent post-processing failed: {e}")
        response_payload["selected_agent"] = "Research Paper Agent"
        response_payload["intent"] = "paper_analysis"

    db.save_document(
        session_id,
        filename,
        str(filepath),
        response_payload,
        full_text=full_text,
        chunks=chunks,
        chunk_records=chunk_records,
    )
    db.clear_chat_history(session_id)
    if job_id:
        job_manager.update(job_id, progress=95, message="Saving document workspace")
    return response_payload


# Multi-agent runtime
llm_service = LLMService(get_active_gemini_engine)
ocr_service = OCRService()
audio_service = AudioService()
github_service = GitHubService()

research_agent = ResearchPaperAgent(llm_service)
rag_agent = RAGRetrievalAgent(
    qa_engine=qa_engine,
    gemini_provider=get_active_gemini_engine,
    ensure_search_index=ensure_search_index,
    bounded_context=bounded_context,
    db=db,
)
math_agent = MathEquationAgent(ocr_service=ocr_service, llm_service=llm_service)
code_agent = CodeGenerationAgent(llm_service=llm_service)
citation_agent = CitationAgent(scholarly_service=ScholarlyService, llm_service=llm_service)
github_agent = GitHubRepoMatcherAgent(github_service=github_service)
podcast_agent = PodcastAgent(audio_service=audio_service, llm_service=llm_service)

orchestrator_agent = OrchestratorAgent(
    agents={
        "research": research_agent,
        "rag": rag_agent,
        "math": math_agent,
        "code": code_agent,
        "citation": citation_agent,
        "github": github_agent,
        "podcast": podcast_agent,
    },
    db=db,
)

system_health = SystemHealthService(
    db=db,
    embedding_engine=embedding_engine,
    job_manager=job_manager,
    rate_limiter=rate_limiter,
    gemini_provider=get_active_gemini_engine,
    runtime_warnings_provider=validate_runtime_environment,
)

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.route("/health", methods=["GET"])
def health():
    """API health status, dependencies, and active runtime configuration."""
    gemini = get_active_gemini_engine()
    snapshot = system_health.snapshot()
    status_code = 503 if snapshot["status"] == "down" else 200
    return jsonify({
        **snapshot,
        "message": "Scientia.ai Research Assistant API is running",
        "mode": "advanced (Gemini)" if gemini.is_available else "offline (fast local fallback)",
        "retrieval": "semantic" if embedding_engine.use_semantic else "lexical",
        "transformer_fallback": bool(getattr(summarizer.config, "USE_TRANSFORMER_FALLBACK", False)),
        "jobs": len(job_manager.list(limit=500)),
        "environment_warnings": validate_runtime_environment(),
    }), status_code

@app.route("/upload", methods=["POST"])
def upload():
    """
    Upload a research paper. Clean text, build FAISS local vector index,
    and analyze paper using Gemini (fast & deep) or Local pipelines.
    """
    global _active_index_key
    started_at = time.perf_counter()
    timings = {}
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
        timings["save_ms"] = round((time.perf_counter() - started_at) * 1000)
    except Exception as e:
        logger.error(f"Failed to save file: {e}")
        return jsonify({"error": f"Failed to save file: {str(e)}"}), 500

    wants_async = str(request.args.get("async", request.form.get("async", ""))).lower() in {"1", "true", "yes"}
    if wants_async:
        try:
            job_id = job_manager.submit("pdf_upload", process_saved_pdf, filepath, filename, save_name)
        except JobQueueFull as exc:
            return api_error(str(exc), 429, "job_queue_full")
        return jsonify({
            "job_id": job_id,
            "status": "queued",
            "status_url": f"/api/jobs/{job_id}",
            "message": "PDF upload accepted. Processing continues in the background.",
        }), 202

    try:
        response_payload = process_saved_pdf(filepath=filepath, filename=filename, save_name=save_name)
        return jsonify(response_payload)
    except ValueError as e:
        logger.error(f"Failed to process PDF: {e}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Failed to process PDF: {e}")
        return jsonify({"error": f"Failed to process PDF: {str(e)}"}), 500

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

    started_at = time.perf_counter()
    # Parse potential multiple session IDs
    session_ids = [s.strip() for s in session_id.split(",") if s.strip()]

    try:
        indexed_chunks = ensure_search_index(session_ids)
    except Exception as e:
        logger.error(f"Failed to prepare search index: {e}")
        return jsonify({"error": str(e)}), 400


    try:
        relevant_chunks = qa_engine.get_relevant_chunks(question)
    except Exception as e:
        logger.error(f"Failed to retrieve chunks: {e}")
        relevant_chunks = []

    context = bounded_context(relevant_chunks)
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
        logger.info("Answering using fast local extractive model")
        try:
            answer, _ = qa_engine.answer(question)
        except Exception as e:
            logger.error(f"Local QA failed: {e}")
            answer = "Sorry, failed to generate an answer using local model fallback."

    # Save user/AI exchanges to SQLite
    try:
        db.add_chat_msg(session_id, "user", question)
        db.add_chat_msg(session_id, "assistant", answer, relevant_chunks)
        db.log_chat(
            session_id=session_id,
            user_query=question,
            selected_agent="RAG Retrieval Agent",
            intent="source_grounded_qa",
            response=answer,
            sources=relevant_chunks[:3],
        )
        db.log_agent(
            selected_agent="RAG Retrieval Agent",
            intent="source_grounded_qa",
            query=question,
            response=answer,
            metadata={"session_id": session_id, "retrieved_chunks": len(relevant_chunks)},
        )
    except Exception as e:
        logger.error(f"Failed to log chat interaction: {e}")

    return jsonify({
        "answer": answer,
        "response": answer,
        "selected_agent": "RAG Retrieval Agent",
        "intent": "source_grounded_qa",
        "relevant_sections": relevant_chunks[:3],
        "sources": relevant_chunks[:3],
        "session_id": session_id,
        "performance": {
            "mode": "gemini" if gemini.is_available and not gemini_failed else "local_extractive",
            "indexed_chunks": indexed_chunks,
            "retrieved_chunks": len(relevant_chunks),
            "total_ms": round((time.perf_counter() - started_at) * 1000),
        }
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
    global _active_index_key
    if request.method == "DELETE":
        try:
            db.delete_document(doc_id)
            # If the deleted paper was the active one, clear FAISS index state
            if _active_index_key and doc_id in _active_index_key.split(","):
                embedding_engine._index = None
                embedding_engine._chunks = []
                embedding_engine._lexical_vectors = []
                embedding_engine._lexical_norms = []
                _active_index_key = None
            return jsonify({"status": "success", "message": f"Document {doc_id} deleted."})
        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            return jsonify({"error": str(e)}), 500
    
    # GET method
    try:
        doc = db.get_document(doc_id)
        if not doc:
            return jsonify({"error": "Document not found"}), 404
        
        # Load local search index for this paper using cached chunks when available.
        try:
            ensure_search_index([doc_id])
        except Exception as e:
            logger.error(f"Search index lazy load failed: {e}")
        
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
            invalidate_gemini_cache()
            return jsonify({"status": "success", "message": "API settings updated successfully."})
        except Exception as e:
            logger.error(f"Failed to save setting: {e}")
            return jsonify({"error": str(e)}), 500

    # GET method
    try:
        saved_key = db.get_setting("gemini_api_key", "")
        env_key = os.environ.get("GEMINI_API_KEY", os.environ.get("GOOGLE_API_KEY", ""))
        active_key = saved_key if GeminiEngine.is_valid_api_key(saved_key) else env_key
        has_key = GeminiEngine.is_valid_api_key(active_key)
        # Mask the key for security before returning
        return jsonify({
            "has_key": has_key,
            "masked_key": GeminiEngine.mask_api_key(active_key),
            "source": "saved" if GeminiEngine.is_valid_api_key(saved_key) else ("environment" if has_key else "")
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
        result = gemini.generate_json(prompt)
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
        full_text, _ = load_document_text_and_chunks(session_id)

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
        full_text, _ = load_document_text_and_chunks(session_id)

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

        code = gemini.generate_text(prompt)
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

        code_path = write_text_artifact(
            GENERATED_CODE_FOLDER,
            artifact_filename("code", session_id, "generated_model.py"),
            code,
        )
        output_id = db.save_generated_output(
            session_id=session_id,
            output_type="code",
            title=Path(code_path).name,
            content=code,
            file_path=code_path,
            metadata={"source": "legacy_synthesize_code", "filename": doc.get("filename", "")},
        )

        return jsonify({
            "status": "success",
            "code": code,
            "output_id": output_id,
            "download_url": f"/api/generated-outputs/{output_id}/download",
        })
    except Exception as e:
        logger.error(f"Failed to synthesize code: {e}")
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Multi-agent /api routes
# ---------------------------------------------------------------------------

def _load_doc_context(session_id: str) -> tuple:
    if not session_id:
        return None, "", []
    doc = db.get_document(session_id)
    if not doc:
        raise ValueError("Document not found")
    full_text, chunks = load_document_text_and_chunks(session_id)
    return doc, full_text, chunks


def _save_upload_file(file, allowed_extensions, prefix: str) -> Path:
    if not file or not file.filename:
        raise ValueError("No file was uploaded.")
    validate_extension(file.filename, allowed_extensions)
    filename = secure_filename(file.filename)
    stem, ext = os.path.splitext(filename)
    save_name = f"{prefix}_{stem}_{str(uuid.uuid4())[:8]}{ext.lower()}"
    filepath = UPLOAD_FOLDER / save_name
    file.save(str(filepath))
    return filepath


def api_chat_handler():
    data = request.get_json(silent=True) or {}
    query = (data.get("query") or data.get("message") or data.get("question") or "").strip()
    session_id = (data.get("session_id") or data.get("document_id") or "").strip()
    if not query:
        return jsonify({"error": "Empty query. Please enter a question or task."}), 400

    doc, full_text, _ = (None, "", [])
    if session_id:
        try:
            doc, full_text, _ = _load_doc_context(session_id)
        except Exception as e:
            return jsonify({"error": str(e)}), 404

    payload = {
        "agent": data.get("agent"),
        "repo_links": data.get("repo_links") or [],
        "generate_audio": bool(data.get("generate_audio", True)),
    }
    result = orchestrator_agent.run(
        query=query,
        session_id=session_id,
        payload=payload,
        document_text=full_text,
        filename=(doc or {}).get("filename", ""),
        title=(doc or {}).get("filename", "Research request"),
        summary=(doc or {}).get("summary", {}),
        references=(doc or {}).get("references", {}),
    )

    artifacts = result.get("artifacts", {})
    saved_output_id = None
    try:
        if session_id:
            db.add_chat_msg(session_id, "user", query)
            db.add_chat_msg(session_id, "assistant", result["response"], result.get("sources", []))
        db.log_chat(
            session_id=session_id or "general",
            user_query=query,
            selected_agent=result["selected_agent"],
            intent=result["intent"],
            response=result["response"],
            sources=result.get("sources", []),
        )
        if artifacts.get("code"):
            code_path = write_text_artifact(
                GENERATED_CODE_FOLDER,
                artifact_filename("code", session_id or "general", artifacts.get("filename", "generated_model.py")),
                artifacts["code"],
            )
            artifacts["file_path"] = code_path
            artifacts["download_url"] = ""
            saved_output_id = db.save_generated_output(
                session_id=session_id or "general",
                output_type="code",
                title=Path(code_path).name,
                content=artifacts["code"],
                file_path=code_path,
                metadata=artifacts,
            )
        elif artifacts.get("script") or artifacts.get("audio_path"):
            saved_output_id = db.save_generated_output(
                session_id=session_id or "general",
                output_type="audio" if artifacts.get("audio_path") else "podcast_script",
                title="Podcast briefing",
                content=artifacts.get("script", ""),
                file_path=artifacts.get("audio_path", ""),
                metadata=artifacts,
            )
        elif artifacts.get("latex"):
            saved_output_id = db.save_generated_output(
                session_id=session_id or "general",
                output_type="equation",
                title="Equation analysis",
                content=result["response"],
                metadata=artifacts,
            )
        if saved_output_id:
            artifacts["download_url"] = f"/api/generated-outputs/{saved_output_id}/download"
            result["artifacts"] = artifacts
    except Exception as e:
        logger.error(f"Failed to persist API chat: {e}")

    return jsonify({
        **result,
        "answer": result["response"],
        "relevant_sections": result.get("sources", []),
        "session_id": session_id,
        "output_id": saved_output_id,
        "download_url": artifacts.get("download_url"),
    })


def api_upload_pdf_handler():
    return upload()


def api_upload_image_handler():
    try:
        file = request.files.get("file") or request.files.get("image")
        query = (request.form.get("query") or request.form.get("equation") or "").strip()
        filepath = _save_upload_file(file, IMAGE_EXTENSIONS, "equation")
        result = math_agent.run(query=query, image_path=str(filepath))
        db.save_generated_output(
            session_id="image",
            output_type="equation",
            title=filepath.name,
            content=result["response"],
            file_path=str(filepath),
            metadata=result.get("artifacts", {}),
        )
        db.log_agent(result["selected_agent"], result["intent"], query or filepath.name, result["response"], metadata=result.get("artifacts", {}))
        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Image upload/equation OCR failed: {e}")
        return jsonify({"error": str(e)}), 500


def api_equation_handler():
    try:
        image_path = None
        if request.files:
            file = request.files.get("file") or request.files.get("image")
            image_path = str(_save_upload_file(file, IMAGE_EXTENSIONS, "equation"))
            query = (request.form.get("query") or request.form.get("equation") or "").strip()
        else:
            data = request.get_json(silent=True) or {}
            query = (data.get("equation") or data.get("query") or "").strip()
            image_path = data.get("image_path")

        result = math_agent.run(query=query, image_path=image_path)
        db.save_generated_output(
            session_id="equation",
            output_type="equation",
            title="Equation analysis",
            content=result["response"],
            file_path=image_path or "",
            metadata=result.get("artifacts", {}),
        )
        db.log_agent(result["selected_agent"], result["intent"], query or image_path or "equation", result["response"], metadata=result.get("artifacts", {}))
        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Equation route failed: {e}")
        return jsonify({"error": str(e)}), 500


def api_code_handler():
    data = request.get_json(silent=True) or {}
    session_id = (data.get("session_id") or "").strip()
    query = (data.get("query") or data.get("topic") or data.get("prompt") or "Generate a PyTorch scaffold").strip()
    try:
        doc, full_text, _ = _load_doc_context(session_id) if session_id else (None, "", [])
        result = code_agent.run(
            query=query,
            document_text=full_text,
            filename=(doc or {}).get("filename", ""),
        )
        artifacts = result.get("artifacts", {})
        code = artifacts.get("code", "")
        code_path = write_text_artifact(
            GENERATED_CODE_FOLDER,
            artifact_filename("code", session_id or "general", artifacts.get("filename", "generated_model.py")),
            code,
        )
        artifacts["file_path"] = code_path
        output_id = db.save_generated_output(
            session_id=session_id or "general",
            output_type="code",
            title=Path(code_path).name,
            content=code,
            file_path=code_path,
            metadata=artifacts,
        )
        artifacts["download_url"] = f"/api/generated-outputs/{output_id}/download"
        result["artifacts"] = artifacts
        db.log_agent(result["selected_agent"], result["intent"], query, result["response"], metadata=artifacts)
        return jsonify({
            **result,
            "code": code,
            "status": "success",
            "output_id": output_id,
            "download_url": artifacts["download_url"],
        })
    except Exception as e:
        logger.error(f"Code generation route failed: {e}")
        return jsonify({"error": str(e)}), 500


def api_citations_handler():
    data = request.get_json(silent=True) or {}
    session_id = (data.get("session_id") or "").strip()
    ref_num = data.get("ref_num")
    query = (data.get("query") or "Analyze citations").strip()
    try:
        doc, full_text, _ = _load_doc_context(session_id) if session_id else (None, data.get("text", ""), [])
        result = citation_agent.run(
            query=query,
            document_text=full_text,
            references=(doc or {}).get("references", {}),
            ref_num=str(ref_num) if ref_num else None,
        )
        citations = result.get("artifacts", {}).get("citations", [])
        citation = citations[0] if citations else {}
        scholarly = citation.get("scholarly") or {}
        compatibility = {
            "ref_num": citation.get("ref_num", ref_num),
            "raw_text": citation.get("raw_text", ""),
            "scholarly_found": bool(scholarly),
            "title": scholarly.get("title") or citation.get("raw_text", ""),
            "abstract": scholarly.get("abstract") or citation.get("summary", result["response"]),
            "authors": scholarly.get("authors"),
            "year": scholarly.get("year"),
            "citations": scholarly.get("citations"),
            "url": scholarly.get("url"),
        }
        db.log_agent(result["selected_agent"], result["intent"], query, result["response"], metadata=result.get("artifacts", {}))
        return jsonify({**result, **compatibility, "citation": citation})
    except Exception as e:
        logger.error(f"Citation route failed: {e}")
        return jsonify({"error": str(e)}), 500


def api_github_handler():
    data = request.get_json(silent=True) or {}
    query = (data.get("query") or data.get("topic") or "").strip()
    repo_links = data.get("repo_links") or data.get("repos") or []
    if not query and not repo_links:
        return jsonify({"error": "Provide a research topic or GitHub repository links."}), 400
    result = github_agent.run(query=query, repo_links=repo_links)
    db.log_agent(result["selected_agent"], result["intent"], query or ",".join(repo_links), result["response"], metadata=result.get("artifacts", {}))
    return jsonify({**result, "repositories": result.get("artifacts", {}).get("repositories", [])})


def api_podcast_handler():
    data = request.get_json(silent=True) or {}
    session_id = (data.get("session_id") or "").strip()
    query = (data.get("summary") or data.get("query") or "").strip()
    try:
        if session_id:
            doc, full_text, _ = _load_doc_context(session_id)
            title = doc.get("filename", "Research paper")
            summary_text = query or doc.get("summary", {}).get("abstract", "")
        else:
            full_text = data.get("text", "")
            title = data.get("title", "Research briefing")
            summary_text = query or full_text
            session_id = str(uuid.uuid4())[:8]

        result = podcast_agent.run(
            query=summary_text,
            document_text=full_text,
            title=title,
            session_id=session_id,
            generate_audio=bool(data.get("generate_audio", True)),
            overwrite_audio=bool(data.get("overwrite_audio", True)),
        )
        artifacts = result.get("artifacts", {})
        output_id = db.save_generated_output(
            session_id=session_id,
            output_type="audio" if artifacts.get("audio_path") else "podcast_script",
            title=f"Podcast briefing: {title}",
            content=artifacts.get("script", ""),
            file_path=artifacts.get("audio_path") or "",
            metadata=artifacts,
        )
        artifacts["download_url"] = f"/api/generated-outputs/{output_id}/download"
        result["artifacts"] = artifacts
        db.log_agent(result["selected_agent"], result["intent"], title, result["response"], metadata=artifacts)
        return jsonify({
            **result,
            "status": "success",
            "url": artifacts.get("audio_url"),
            "script": artifacts.get("script"),
            "output_id": output_id,
            "download_url": artifacts["download_url"],
        })
    except Exception as e:
        logger.error(f"Podcast route failed: {e}")
        return jsonify({"error": str(e)}), 500


def api_generated_audio_handler(session_id):
    return send_from_directory(AUDIO_FOLDER, f"{session_id}.mp3", mimetype="audio/mpeg")


@app.route("/api/health", methods=["GET"])
def api_health():
    return health()


@app.route("/api/system/health", methods=["GET"])
def api_system_health():
    snapshot = system_health.snapshot()
    return jsonify(snapshot), 503 if snapshot["status"] == "down" else 200


@app.route("/api/system/readiness", methods=["GET"])
def api_system_readiness():
    snapshot = system_health.readiness()
    return jsonify(snapshot), 200 if snapshot["ready"] else 503


@app.route("/api/system/metrics", methods=["GET"])
def api_system_metrics():
    return jsonify(system_health.metrics())


@app.route("/api/settings", methods=["GET", "POST"])
def api_settings():
    return manage_settings()


@app.route("/api/documents", methods=["GET"])
def api_documents():
    return get_documents()


@app.route("/api/documents/<doc_id>", methods=["GET", "DELETE"])
def api_manage_document(doc_id):
    return manage_document(doc_id)


@app.route("/api/agent-logs", methods=["GET"])
def api_agent_logs():
    limit = request.args.get("limit", "100")
    try:
        limit_int = max(1, min(int(limit), 500))
    except ValueError:
        limit_int = 100
    return jsonify({"agent_logs": db.list_agent_logs(limit=limit_int)})


@app.route("/api/generated-outputs", methods=["GET"])
def api_generated_outputs():
    limit = request.args.get("limit", "100")
    try:
        limit_int = max(1, min(int(limit), 500))
    except ValueError:
        limit_int = 100
    return jsonify({"generated_outputs": db.list_generated_outputs(limit=limit_int)})


@app.route("/api/generated-outputs/<int:output_id>", methods=["GET"])
def api_generated_output_detail(output_id):
    output = db.get_generated_output(output_id)
    if not output:
        return jsonify({"error": "Generated output not found"}), 404
    return jsonify({"generated_output": output})


@app.route("/api/generated-outputs/<int:output_id>/download", methods=["GET"])
def api_generated_output_download(output_id):
    output = db.get_generated_output(output_id)
    if not output:
        return jsonify({"error": "Generated output not found"}), 404

    download_name = artifact_filename("scientia", output.get("session_id") or "general", output.get("title") or "output.txt")
    file_path = output.get("file_path") or ""
    if file_path:
        candidate = Path(file_path).resolve()
        allowed_roots = [
            UPLOAD_FOLDER.resolve(),
            AUDIO_FOLDER.resolve(),
            GENERATED_CODE_FOLDER.resolve(),
            GENERATED_MARKDOWN_FOLDER.resolve(),
        ]
        if candidate.exists() and any(candidate.is_relative_to(root) for root in allowed_roots):
            file_download_name = Path(output.get("title") or "").name
            if not Path(file_download_name).suffix:
                file_download_name = candidate.name
            return send_file(candidate, as_attachment=True, download_name=file_download_name)

    output_type = output.get("output_type") or "text"
    mimetype = "text/plain"
    fallback_name = download_name
    if output_type == "code":
        mimetype = "text/x-python"
        if not Path(fallback_name).suffix:
            fallback_name = f"{fallback_name}.py"
    elif output_type in {"markdown", "summary"}:
        mimetype = "text/markdown"
        if not Path(fallback_name).suffix:
            fallback_name = f"{fallback_name}.md"

    response = app.response_class(output.get("content") or "", mimetype=mimetype)
    response.headers["Content-Disposition"] = f'attachment; filename="{fallback_name}"'
    return response


@app.route("/api/jobs", methods=["GET"])
def api_jobs():
    limit = request.args.get("limit", "50")
    try:
        limit_int = max(1, min(int(limit), 200))
    except ValueError:
        limit_int = 50
    return jsonify({"jobs": job_manager.list(limit=limit_int)})


@app.route("/api/jobs/<job_id>", methods=["GET"])
def api_job_detail(job_id):
    job = job_manager.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify({"job": job})


@app.route("/api/documents/<doc_id>/export/markdown", methods=["GET"])
def api_export_document_markdown(doc_id):
    doc = db.get_document(doc_id)
    if not doc:
        return jsonify({"error": "Document not found"}), 404

    markdown = build_markdown_report(doc)
    filename = artifact_filename("paper_report", doc_id, f"{Path(doc.get('filename', 'paper')).stem}.md")
    file_path = write_text_artifact(GENERATED_MARKDOWN_FOLDER, filename, markdown)
    output_id = db.save_generated_output(
        session_id=doc_id,
        output_type="markdown",
        title=Path(file_path).name,
        content=markdown,
        file_path=file_path,
        metadata={"source": "document_export", "filename": doc.get("filename", "")},
    )
    response = send_file(file_path, as_attachment=True, download_name=Path(file_path).name, mimetype="text/markdown")
    response.headers["X-Generated-Output-Id"] = str(output_id)
    return response


register_chat_routes(app, {"chat": api_chat_handler, "history": history})
register_upload_routes(app, {"upload_pdf": api_upload_pdf_handler, "upload_image": api_upload_image_handler})
register_equation_routes(app, {"equation": api_equation_handler})
register_code_routes(app, {"code": api_code_handler})
register_citation_routes(app, {"citations": api_citations_handler})
register_github_routes(app, {"github": api_github_handler})
register_podcast_routes(app, {"podcast": api_podcast_handler, "generated_audio": api_generated_audio_handler})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=FlaskConfig.DEBUG)



