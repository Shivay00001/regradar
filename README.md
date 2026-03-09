# ⚡ RegRadar — India Regulatory Intelligence Platform

Real-time AI-powered compliance monitoring for Indian businesses.
Monitors RBI, SEBI, MCA, GST, Labour ministry — automatically using free and local AI models.

---

## 🚀 Features

- **Live Scan & Monitoring**: Automatically scrapes official Indian government websites for regulatory updates.
- **AI-Powered Analysis**: Deep analysis of circulars and notifications for actionable compliance steps.
- **Free/Local AI Integration**: Supports 100% free and private AI models via **Ollama**, as well as cloud providers like **Groq** and **Google Gemini**.
- **Interactive Chat**: Ask the AI agent specific compliance questions based on the latest regulations.

---

## ⚙️ Setup Instructions

### 1. Prerequisites

- Python 3.10+
- (Optional) [Ollama](https://ollama.com/) for local, private AI models.

### 2. Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/Shivay00001/regradar.git
cd regradar

# Install required Python packages
pip install -r requirements.txt
```

### 3. Configuration

```bash
cp .env.example .env
```

Edit the `.env` file to select your preferred AI provider:

- **Ollama**: (Default) Runs locally. Make sure Ollama is installed and run `ollama pull llama3.2` (or your preferred model).
- **Groq**: Fast cloud inference. Add your free API key from console.groq.com.
- **Gemini**: Add your free API key from aistudio.google.com.

### 4. Running the Server

```bash
python app.py
```

The application will be available at [http://localhost:3000](http://localhost:3000).

---

## 🏗️ Architecture

- **Backend**: Python with **FastAPI**.
- **Scraping**: `BeautifulSoup4` for real-time extraction from government portals.
- **AI Processing**: Unified interface in `ai_providers.py` for Ollama, Groq, and Gemini.
- **Frontend**: Lightweight HTML/Vanilla JS interface served by the backend.

---

## 📡 API Routes

| Route | Method | What it does |
|-------|--------|--------------|
| `/api/scan` | POST | AI scans government sites, returns real regulations |
| `/api/analyze` | POST | Deep analysis of a specific regulation |
| `/api/chat` | POST | Chat with AI about any regulation |
| `/api/config` | GET | Check active provider configuration |
| `/api/health` | GET | Check server status |

---

## 💼 Use Cases

Targeting CFOs, Legal Heads, and Compliance Officers to reduce regulatory risks and automate compliance tracking across banking, NBFC, capital markets, and corporate sectors.
