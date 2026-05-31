# Scientia.ai - Production AI Research Assistant

Scientia.ai is a state-of-the-art AI Research Assistant designed for advanced academic and technical exploration. It features a multi-agent orchestration system, hybrid RAG pipeline, and a premium React-based research laboratory.

## 🚀 Key Features

- **Multi-Agent Orchestration**: Specialized agents for Planning, Researching, Critiquing, and Writing.
- **Advanced RAG Pipeline**: Hybrid retrieval combining Vector (Sentence Transformers) and BM25 search with Cross-Encoder re-ranking.
- **Document Intelligence**: Deep extraction and analysis of PDF and DOCX documents.
- **Real-Time Web Search**: Integrated with Tavily for up-to-the-minute global research context.
- **Premium Research Lab**: A modern split-panel interface with real-time chat, source viewing, and research timelines.
- **Production Ready**: Full Docker & Kubernetes support with PostgreSQL and Redis integration.

## 🛠️ Tech Stack

- **Backend**: FastAPI, SQLAlchemy, LangChain, Redis, PostgreSQL.
- **Frontend**: React, Tailwind CSS, Lucide Icons, Framer Motion.
- **AI/ML**: Sentence Transformers, Rank-BM25, Whisper (STT), ReportLab.

## 📦 Setup & Installation

### Prerequisites
- Docker & Docker Compose
- API Keys (OpenAI, Tavily) - Add these to a `.env` file.

### Quick Start with Docker
```bash
docker-compose up --build
```

### Manual Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements_prod.txt
uvicorn app.main:app --reload
```

### Manual Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

## 📖 Production Guide
See [PRODUCTION.md](./PRODUCTION.md) for detailed deployment instructions.
