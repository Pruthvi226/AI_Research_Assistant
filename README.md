# Scientia.ai - Production AI Research Assistant

Scientia.ai is a state-of-the-art AI Research Assistant designed for advanced academic and technical exploration. It features a high-fidelity dark glassmorphic dashboard, dual-voice neural audio podcast compiler, interactive LaTeX playground simulators, PyTorch neural scaffold synthesizers, and dynamic EuropePMC/OpenAlex citation references drawers.

---

## 🚀 Next-Generation Features

- **📐 Math OCR & LaTeX Typesetting**: Extracts complex LaTeX math equations and renders them in real-time in both chat feeds and playground cards using KaTeX.
- **🧪 LaTeX Equation Solver & Simulator**: Renders custom sliders for formula variables and displays dynamic, animated SVG circular load level gauges evaluating system output in real-time.
- **💻 PyTorch Code Compiler & GitHub Repo Matcher**: Compiles robust, highly-commented PyTorch custom layers, modules, and training boilerplates based on the active paper's methodology, alongside community repository maps utilizing GitHub search APIs.
- **🎙️ NotebookLM-Style Audio Podcast Overviews**: Compiles technical technical papers into engaging, multi-voice dialog scripts streamed natively in a custom React sound player.
- **🔗 Scholarly Citation Drawer**: Clicking bracketed citations (`[1]`) fetches peer abstracts, publication years, stargazers, and PDF download links on-the-fly via the OpenAlex API.
- **📊 Cross-Paper Comparative Synthesis**: Aggregates methodology, datasets, parameters, and accuracy metrics side-by-side inside structured comparative tables.
- **🐳 Multi-Tenant SQLite Vector RAG**: Fully isolated semantic chunks stored in localized FAISS indices, bridged with a low-latency Flask backend and Google Gemini Flash model.

---

## 📦 Setup & Installation

### Quick Start with Docker
You can boot the entire containerized production environment (Nginx route proxy + static React + Flask server + SQLite database volume persist) with a single command:
```bash
docker-compose up --build
```
Once built, open **http://localhost:3000** in your browser.

### Manual Backend Setup
```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
python app.py
```
Server runs at **http://localhost:5000**.

### Manual Frontend Setup
```bash
cd frontend
npm install
npm start
```
App dev server runs at **http://localhost:3000** and proxies API requests.

---

## 🧪 Verification & Audits
Scientia.ai incorporates an automated readiness test suite:
```bash
python C:\Users\pruthviraj\.gemini\antigravity\brain\2e68f384-be28-4936-8b23-c5820ffedf49\scratch\verify_all.py
```
All system compiles, database connection lockouts, scholary reconstructors, Nginx proxies, and postgres alpine compose targets pass successfully.

---

## 📖 Production Guide
See [PRODUCTION.md](./PRODUCTION.md) for detailed deployment instructions.

## License
MIT.
