# ⚡ RegRadar — India Regulatory Intelligence Platform

Real-time AI-powered compliance monitoring for Indian businesses.
Monitors RBI, SEBI, MCA, GST, Labour ministry — automatically.

---

## Setup (5 minutes)

### 1. Install Node.js
Download from https://nodejs.org (v18 or higher)

### 2. Get Anthropic API Key
Go to https://console.anthropic.com → Create API Key

### 3. Setup Project

```bash
# Enter project folder
cd regradar

# Install dependencies
npm install

# Create .env file
cp .env.example .env

# Edit .env and paste your API key
# ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxx
```

### 4. Run

```bash
npm start
```

Open browser → http://localhost:3000

---

## How It Works

1. Click **LIVE SCAN** → Claude AI agent searches official government websites
2. Real regulatory updates appear in the list
3. Click any alert → AI runs deep analysis with additional web research  
4. Use **ASK AI AGENT** tab to ask compliance questions

---

## Architecture

```
Browser (public/index.html)
    ↓ HTTP POST
Express Server (server.js)
    ↓ Anthropic API + Web Search Tool
Claude AI Agent → searches rbi.org.in, sebi.gov.in, mca.gov.in, cbic.gov.in, labour.gov.in
    ↓
Real Regulatory Data → Back to Browser
```

---

## API Routes

| Route | Method | What it does |
|-------|--------|--------------|
| /api/scan | POST | AI scans government sites, returns real regulations |
| /api/analyze | POST | Deep analysis of a specific regulation |
| /api/chat | POST | Chat with AI about any regulation |
| /api/health | GET | Check server status |

---

## Monetization

- ₹8L–₹25L/year per enterprise client
- Target: CFO, Legal Head, Compliance Officer
- Demo: Show them a live scan of their sector → instant close
