"""
RegRadar — FastAPI Backend
Real-time Indian Regulatory Intelligence Platform.
Fully functional with free/local AI (Ollama, Groq, Gemini).
"""

import os
import re
import json
import time
import traceback
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from dotenv import load_dotenv

load_dotenv()

from ai_providers import call_ai, call_ai_chat, get_provider_config, check_provider_health
from scraper import scrape_source, scrape_url_content

app = FastAPI(title="RegRadar", description="India Regulatory Intelligence Platform")

# ─── Serve static files ─────────────────────────────────────────────────────────
PUBLIC_DIR = os.path.join(os.path.dirname(__file__), "public")
app.mount("/public", StaticFiles(directory=PUBLIC_DIR), name="public")


# ─── Health Check ────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    config = get_provider_config()
    return {
        "status": "ok",
        "provider": config["display"],
        "model": config["model"],
        "timestamp": datetime.now().isoformat(),
    }


# ─── Provider Config ────────────────────────────────────────────────────────────

@app.get("/api/config")
def config():
    config = get_provider_config()
    health = check_provider_health()
    return {
        "provider": config["display"],
        "model": config["model"],
        "provider_name": config["name"],
        "health": health,
    }


# ─── Live Scan ───────────────────────────────────────────────────────────────────

SCAN_SYSTEM_PROMPT = """You are RegRadar's regulatory intelligence analyst for India.

You will receive scraped data from official Indian government websites (RBI, SEBI, MCA, GST/CBIC, Labour Ministry).

Your job: Parse the scraped data and return ONLY a valid JSON array of the most important regulatory updates.
No markdown. No explanation. No code fences. Start directly with [ and end with ].

Each item must have this exact structure:
[
  {
    "source": "RBI",
    "title": "exact title of circular or notification",
    "date": "YYYY-MM-DD",
    "sector": ["Banking", "NBFC"],
    "impact": "High",
    "tag": "KYC / AML",
    "url": "actual official url from scraped data",
    "summary": "2-3 sentence plain English summary of what this regulation does",
    "what_changed": "specific change in 1 sentence",
    "who_affected": "exact entities or roles affected",
    "action_required": ["action 1", "action 2", "action 3"],
    "deadline": "specific date or timeframe if mentioned",
    "risk": "penalty or consequence if ignored"
  }
]

Rules:
- Impact: High = action needed within 30 days, Medium = plan within 90 days, Low = awareness
- Use real titles and URLs from the scraped data
- If you can't determine a field, make a reasonable inference based on the source and title
- Return 4-6 items minimum
- Infer the sector from the source: RBI→Banking/NBFC, SEBI→Capital Markets, MCA→Corporate, GST→Taxation, LABOUR→Employment
- IMPORTANT: Return ONLY the JSON array, nothing else"""


@app.post("/api/scan")
async def scan(request: Request):
    try:
        body = await request.json()
    except:
        body = {}

    source = body.get("source", "All")

    try:
        print(f"\n[SCAN] Starting scan: {source}")

        # Step 1: Scrape official sites
        print("[SCAN] Step 1: Scraping official government websites...")
        scraped_data = scrape_source(source)

        if not scraped_data:
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": "Scraper returned no data. Government sites may be unreachable."}
            )

        # Step 2: Format scraped data for AI
        scraped_text = "Here are the regulatory items scraped from official Indian government websites:\n\n"
        for i, item in enumerate(scraped_data, 1):
            scraped_text += f"{i}. [{item['source']}] {item['title']}\n"
            scraped_text += f"   URL: {item['url']}\n"
            scraped_text += f"   Date: {item['date']}\n"
            if item.get('raw_text'):
                scraped_text += f"   Context: {item['raw_text'][:200]}\n"
            scraped_text += "\n"

        scraped_text += f"\nTotal scraped items: {len(scraped_data)}"
        scraped_text += "\n\nParse these into the JSON format specified. Create realistic and detailed entries for each item."

        # Step 3: AI processes scraped data
        print("[SCAN] Step 2: AI processing scraped regulatory data...")
        raw = call_ai(SCAN_SYSTEM_PROMPT, scraped_text, max_tokens=6000)

        # Extract JSON array
        # Try to find JSON array in response
        match = re.search(r'\[[\s\S]*\]', raw)
        if not match:
            # If AI didn't return JSON, create structured data from scraped items
            print("[SCAN] AI did not return JSON, creating from scraped data...")
            regulations = []
            for item in scraped_data[:6]:
                source_map = {
                    "RBI": ["Banking", "NBFC"],
                    "SEBI": ["Capital Markets", "Securities"],
                    "MCA": ["Corporate", "Companies Act"],
                    "GST": ["Taxation", "GST"],
                    "LABOUR": ["Employment", "Labour Law"],
                }
                regulations.append({
                    "source": item["source"],
                    "title": item["title"],
                    "date": item["date"],
                    "sector": source_map.get(item["source"], ["General"]),
                    "impact": "Medium",
                    "tag": "Regulatory Update",
                    "url": item["url"],
                    "summary": f"Regulatory update from {item['source']}: {item['title'][:150]}",
                    "what_changed": item["title"][:100],
                    "who_affected": f"Entities regulated by {item['source']}",
                    "action_required": ["Review the notification", "Assess applicability", "Plan compliance steps"],
                    "deadline": "Check official circular",
                    "risk": "Non-compliance penalties as per regulatory framework",
                })
        else:
            try:
                regulations = json.loads(match[0])
            except json.JSONDecodeError:
                # Fallback: create from scraped data
                print("[SCAN] JSON parse failed, creating from scraped data...")
                regulations = []
                for item in scraped_data[:6]:
                    regulations.append({
                        "source": item["source"],
                        "title": item["title"],
                        "date": item["date"],
                        "sector": [item["source"]],
                        "impact": "Medium",
                        "tag": "Update",
                        "url": item["url"],
                        "summary": item["title"],
                        "what_changed": item["title"][:100],
                        "who_affected": f"{item['source']} regulated entities",
                        "action_required": ["Review notification"],
                        "deadline": "See official source",
                        "risk": "Regulatory non-compliance",
                    })

        if not isinstance(regulations, list) or len(regulations) == 0:
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": "Could not parse regulatory data"}
            )

        # Add metadata
        with_meta = []
        for i, r in enumerate(regulations):
            r["id"] = f"reg_{int(time.time())}_{i}"
            r["scannedAt"] = datetime.now().isoformat()
            with_meta.append(r)

        print(f"[SCAN] Found {len(with_meta)} regulations from {source}")
        return {"success": True, "count": len(with_meta), "source": source, "regulations": with_meta}

    except Exception as e:
        print(f"[SCAN ERROR] {e}")
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


# ─── Deep Analysis ───────────────────────────────────────────────────────────────

ANALYSIS_SYSTEM_PROMPT = """You are RegRadar's senior compliance analyst for India.

Format your response exactly as below. Use ** for section headers:

**WHAT CHANGED**
[2-3 sentences in plain English explaining the regulatory change]

**WHO IS AFFECTED**
[Specific entities, departments, company types, roles]

**IMMEDIATE ACTIONS REQUIRED**
• [specific action 1]
• [specific action 2]
• [specific action 3]
• [specific action 4 if applicable]

**DEADLINE**
[Specific date or "Immediate" or specific timeframe]

**PENALTY / RISK IF IGNORED**
[Exact financial penalty if known, legal risk, operational impact]

**COMPLIANCE CHECKLIST**
• [ ] [Step 1 — who does what]
• [ ] [Step 2]
• [ ] [Step 3]
• [ ] [Step 4]
• [ ] [Step 5]

**RELATED CIRCULARS**
[Any prior circulars or regulations this builds on — use your knowledge]

Write for a CFO or Legal Head. Be specific with numbers and dates. No fluff."""


@app.post("/api/analyze")
async def analyze(request: Request):
    body = await request.json()
    regulation = body.get("regulation")

    if not regulation:
        return JSONResponse(status_code=400, content={"error": "regulation object required"})

    try:
        print(f"[ANALYZE] {regulation.get('source')} — {regulation.get('title')}")

        # Try to scrape additional content from the URL
        extra_context = ""
        url = regulation.get("url", "")
        if url and url.startswith("http"):
            print(f"[ANALYZE] Scraping additional context from {url[:60]}...")
            extra_content = scrape_url_content(url)
            if extra_content:
                extra_context = f"\n\nAdditional content scraped from official source:\n{extra_content[:2000]}"

        user_msg = f"""Deep analyze this Indian regulatory update:

Source: {regulation.get('source', 'Unknown')}
Title: {regulation.get('title', 'Unknown')}
Date: {regulation.get('date', 'Unknown')}
Sectors: {', '.join(regulation.get('sector', []))}
Tag: {regulation.get('tag', '')}
Summary: {regulation.get('summary', '')}
URL: {url or 'not available'}
What Changed: {regulation.get('what_changed', '')}
Risk: {regulation.get('risk', '')}
{extra_context}

Provide complete executive intelligence briefing with specific compliance actions."""

        analysis = call_ai(ANALYSIS_SYSTEM_PROMPT, user_msg, max_tokens=3000)
        return {"success": True, "analysis": analysis}

    except Exception as e:
        print(f"[ANALYZE ERROR] {e}")
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


# ─── Chat ────────────────────────────────────────────────────────────────────────

@app.post("/api/chat")
async def chat(request: Request):
    body = await request.json()
    messages = body.get("messages")
    regulation = body.get("regulation")

    if not messages or not isinstance(messages, list):
        return JSONResponse(status_code=400, content={"error": "messages array required"})

    system = f"""You are RegRadar's AI compliance advisor for India.
Current regulation context: "{regulation.get('title', 'Indian regulatory matters') if regulation else 'Indian regulatory matters'}" from {regulation.get('source', 'Indian regulators') if regulation else 'Indian regulators'} dated {regulation.get('date', 'recent') if regulation else 'recent'}.
Sector: {', '.join(regulation.get('sector', ['General'])) if regulation else 'General'}

Answer like a senior compliance consultant — concise, actionable, specific.
Use your knowledge of Indian regulations to give accurate answers.
Always mention relevant sections, rules, or circular numbers when possible."""

    try:
        print(f"[CHAT] User: {messages[-1].get('content', '')[:60]}...")
        reply = call_ai_chat(system, messages, max_tokens=2000)
        return {"success": True, "reply": reply}

    except Exception as e:
        print(f"[CHAT ERROR] {e}")
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


# ─── Serve Frontend ─────────────────────────────────────────────────────────────

@app.get("/")
def serve_frontend():
    return FileResponse(os.path.join(PUBLIC_DIR, "index.html"))


@app.get("/{path:path}")
def catch_all(path: str):
    # Try to serve from public directory first
    file_path = os.path.join(PUBLIC_DIR, path)
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    return FileResponse(os.path.join(PUBLIC_DIR, "index.html"))


# ─── Main ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 3000))
    config = get_provider_config()
    health = check_provider_health()

    print(f"\n⚡ RegRadar starting...")
    print(f"   Provider: {config['display']}")
    print(f"   Model: {config['model']}")
    print(f"   Health: {health.get('status', 'unknown')}")
    if health.get("error"):
        print(f"   ⚠️  {health['error']}")
    print(f"   URL: http://localhost:{port}\n")

    uvicorn.run(app, host="0.0.0.0", port=port)
