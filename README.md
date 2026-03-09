# AI Research Assistant

A production-ready web application that lets you **upload a research paper PDF** and get an **AI summary**, **key contributions**, **future research ideas**, and **semantic Q&A** over the document. Built with Flask, React, FAISS, Sentence Transformers, and HuggingFace Transformers.

---

## Features

- **PDF upload** – Extract and clean text from research papers (references section removed).
- **AI summary** – Abstract and section-wise summaries via BART.
- **Key contributions** – Automatically extracted from the paper.
- **Future research directions** – Suggested follow-up ideas.
- **Research gap detection** – Identifies unexplored areas.
- **Suggested paper titles** – New title ideas based on the research.
- **Important sentences** – Highlighted key sentences.
- **Chat with paper** – Ask questions and get answers grounded in the document (FAISS + semantic search).
- **Conversation history** – Stored per session.
- **Modern UI** – React + Tailwind; layout: upload/summary (left), chat (right), insights (bottom).

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Frontend (React)                             │
│  UploadPaper │ SummaryPanel │ ChatInterface │ InsightsPanel      │
└───────────────────────────────┬─────────────────────────────────┘
                                │ REST API (Axios)
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Flask Backend                                │
│  POST /upload  │  POST /ask  │  GET /health  │  GET /history     │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     AI Pipeline                                  │
│  PDFProcessor → TextChunker → EmbeddingEngine (FAISS)            │
│       ↓              ↓                    ↓                      │
│  PyMuPDF      Semantic chunks      Sentence Transformers         │
│       ↓              ↓                    ↓                      │
│  PaperSummarizer    ResearchInsightsEngine    QAEngine            │
│  (BART)             (contributions, gaps)    (search + answer)    │
└─────────────────────────────────────────────────────────────────┘
```

**Data flow**

1. **Upload** – PDF → `PDFProcessor` → full text → `TextChunker` → chunks → `EmbeddingEngine.create_index()` (FAISS) → `PaperSummarizer` + `ResearchInsightsEngine` → response to frontend.
2. **Ask** – Question → `EmbeddingEngine.search()` → top chunks → `QAEngine.answer()` (summarize as answer) → `ChatMemory.add()` → response with answer + relevant sections.

---

## Project structure

```
ai-research-assistant/
├── backend/
│   ├── app.py              # Flask API
│   ├── config.py           # Settings
│   ├── pdf_processor.py    # PDF extraction (PyMuPDF)
│   ├── text_chunker.py     # Semantic chunking
│   ├── embeddings_engine.py # Sentence Transformers + FAISS
│   ├── summarizer.py       # BART summarization
│   ├── research_insights.py # Contributions, gaps, titles
│   ├── qa_engine.py        # Question answering
│   ├── chat_memory.py      # Conversation history
│   └── requirements.txt
├── frontend/
│   ├── public/
│   │   └── index.html
│   ├── src/
│   │   ├── components/
│   │   │   ├── UploadPaper.js
│   │   │   ├── SummaryPanel.js
│   │   │   ├── ChatInterface.js
│   │   │   └── InsightsPanel.js
│   │   ├── App.js
│   │   ├── api.js
│   │   ├── index.js
│   │   └── index.css
│   ├── package.json
│   ├── tailwind.config.js
│   └── postcss.config.js
├── uploads/                 # Uploaded PDFs (created automatically)
└── README.md
```

---

## Setup

### Backend (Python 3.9+)

1. Create and activate a virtual environment (recommended):

   ```bash
   cd backend
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # macOS/Linux:
   source venv/bin/activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run the API:

   ```bash
   python app.py
   ```

   Server runs at **http://localhost:5000**. First request may be slower while models download (Sentence Transformers, BART).

### Frontend (Node 18+)

1. Install dependencies:

   ```bash
   cd frontend
   npm install
   ```

2. Start the dev server:

   ```bash
   npm start
   ```

   App runs at **http://localhost:3000** and proxies API requests to the backend via `package.json` proxy.

### Running both

- Terminal 1: `cd backend && python app.py`
- Terminal 2: `cd frontend && npm start`
- Open **http://localhost:3000**, upload a PDF, then use summary, insights, and chat.

---

## API

| Method | Endpoint   | Description |
|--------|------------|-------------|
| GET    | `/health`  | Health check. |
| POST   | `/upload`  | Body: `multipart/form-data` with `file` (PDF). Returns summary, key_contributions, future_research, limitations, research_gaps, suggested_titles, important_sentences, session_id. |
| POST   | `/ask`     | Body: `{ "question": "...", "session_id": "..." }`. Returns answer and relevant_sections. |
| GET    | `/history` | Query: `session_id`. Returns conversation history. |

---

## Demo

1. **Upload** – Choose a research paper PDF (e.g. from arXiv).
2. **Summary** – Abstract and section summaries appear in the left panel.
3. **Insights** – Bottom panel shows contributions, future research, limitations, gaps, suggested titles, important sentences.
4. **Chat** – Type a question (e.g. “What is the main method?”). Answer and “Relevant sections” are shown; history is stored for the session.

---

## Tech stack

- **Backend:** Python, Flask, Flask-CORS, PyMuPDF, Sentence Transformers (`all-MiniLM-L6-v2`), FAISS, Transformers (BART `facebook/bart-large-cnn`).
- **Frontend:** React 18, Tailwind CSS, Axios.

---



## License

MIT.
