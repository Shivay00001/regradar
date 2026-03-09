require("dotenv").config();
const express = require("express");
const cors = require("cors");
const fetch = require("node-fetch");
const path = require("path");

const app = express();
app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, "public")));

const API_KEY = process.env.ANTHROPIC_API_KEY;
const MODEL = "claude-sonnet-4-20250514";

if (!API_KEY) {
  console.error("\n❌ ANTHROPIC_API_KEY not set in .env file\n");
  process.exit(1);
}

// ─── Claude API caller with web search ────────────────────────────────────────
async function callClaude(system, userMessage, maxTokens = 8000) {
  const body = {
    model: MODEL,
    max_tokens: maxTokens,
    system,
    tools: [{ type: "web_search_20250305", name: "web_search" }],
    messages: [{ role: "user", content: userMessage }],
  };

  const res = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": API_KEY,
      "anthropic-version": "2023-06-01",
    },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Anthropic API error ${res.status}: ${err}`);
  }

  const data = await res.json();
  return data.content?.map((c) => c.text || "").join("") || "";
}

// ─── Multi-turn chat caller with web search ───────────────────────────────────
async function callClaudeChat(system, messages, maxTokens = 2000) {
  const body = {
    model: MODEL,
    max_tokens: maxTokens,
    system,
    tools: [{ type: "web_search_20250305", name: "web_search" }],
    messages,
  };

  const res = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": API_KEY,
      "anthropic-version": "2023-06-01",
    },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Anthropic API error ${res.status}: ${err}`);
  }

  const data = await res.json();
  return data.content?.map((c) => c.text || "").join("") || "";
}

// ─── ROUTE: Health check ──────────────────────────────────────────────────────
app.get("/api/health", (req, res) => {
  res.json({ status: "ok", model: MODEL, timestamp: new Date().toISOString() });
});

// ─── ROUTE: Live Scan ─────────────────────────────────────────────────────────
app.post("/api/scan", async (req, res) => {
  const { source = "All" } = req.body;

  const queries = {
    All: "Search for the 6 most important and recent Indian regulatory changes from RBI, SEBI, MCA, GST council, and Labour ministry in the last 30 days. Search each official government website.",
    RBI: "Search rbi.org.in for the latest 4-5 RBI circulars, master directions, and notifications issued in the last 30 days.",
    SEBI: "Search sebi.gov.in for the latest 4-5 SEBI circulars and notifications issued in the last 30 days.",
    MCA: "Search mca.gov.in for the latest 4-5 MCA notifications and Companies Act amendments in the last 30 days.",
    GST: "Search cbic.gov.in and gst.gov.in for the latest 4-5 GST circulars and notifications in the last 30 days.",
    LABOUR: "Search labour.gov.in for the latest 4-5 labor law notifications and amendments in the last 30 days.",
  };

  const system = `You are RegRadar's real-time regulatory intelligence agent for India.

Use web_search to find REAL, CURRENT regulatory changes from these official sources:
- rbi.org.in
- sebi.gov.in  
- mca.gov.in
- cbic.gov.in / gst.gov.in
- labour.gov.in
- egazette.nic.in

After searching, return ONLY a valid JSON array. No markdown. No explanation. Start directly with [:

[
  {
    "source": "RBI",
    "title": "exact title of circular or notification",
    "date": "YYYY-MM-DD",
    "sector": ["NBFC", "Banking"],
    "impact": "High",
    "tag": "KYC / AML",
    "url": "actual official url",
    "summary": "2-3 sentence plain English summary of what changed",
    "what_changed": "specific change in 1 sentence",
    "who_affected": "exact entities or roles affected",
    "action_required": ["action 1", "action 2", "action 3"],
    "deadline": "specific date or timeframe",
    "risk": "penalty or consequence if ignored"
  }
]

Impact definition: High = immediate action needed within 30 days, Medium = plan required within 90 days, Low = awareness only.
Find minimum 5 real regulatory updates.`;

  try {
    console.log(`[SCAN] Starting scan: ${source}`);
    const raw = await callClaude(system, queries[source] || queries["All"]);

    // Extract JSON array robustly
    const match = raw.match(/\[[\s\S]*\]/);
    if (!match) throw new Error("No JSON array found in agent response");

    const regulations = JSON.parse(match[0]);
    if (!Array.isArray(regulations) || regulations.length === 0) {
      throw new Error("Agent returned empty results");
    }

    const withMeta = regulations.map((r, i) => ({
      ...r,
      id: `reg_${Date.now()}_${i}`,
      scannedAt: new Date().toISOString(),
    }));

    console.log(`[SCAN] Found ${withMeta.length} regulations from ${source}`);
    res.json({ success: true, count: withMeta.length, source, regulations: withMeta });
  } catch (err) {
    console.error("[SCAN ERROR]", err.message);
    res.status(500).json({ success: false, error: err.message });
  }
});

// ─── ROUTE: Deep Analysis ─────────────────────────────────────────────────────
app.post("/api/analyze", async (req, res) => {
  const { regulation } = req.body;
  if (!regulation) return res.status(400).json({ error: "regulation object required" });

  const system = `You are RegRadar's senior compliance analyst for India. 
Use web_search to find additional details, clarifications, or related circulars.

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
[Any prior circulars or regulations this builds on]

Write for a CFO or Legal Head. Be specific with numbers and dates. No fluff.`;

  const userMsg = `Deep analyze this Indian regulatory update. Search for additional details and any related notifications:

Source: ${regulation.source}
Title: ${regulation.title}
Date: ${regulation.date}
Sectors: ${regulation.sector?.join(", ")}
Tag: ${regulation.tag}
Summary: ${regulation.summary}
URL: ${regulation.url || "search for official source"}
What Changed: ${regulation.what_changed}
Risk: ${regulation.risk}

Provide complete executive intelligence briefing with specific compliance actions.`;

  try {
    console.log(`[ANALYZE] ${regulation.source} — ${regulation.title}`);
    const analysis = await callClaude(system, userMsg, 3000);
    res.json({ success: true, analysis });
  } catch (err) {
    console.error("[ANALYZE ERROR]", err.message);
    res.status(500).json({ success: false, error: err.message });
  }
});

// ─── ROUTE: Chat with AI Agent ────────────────────────────────────────────────
app.post("/api/chat", async (req, res) => {
  const { messages, regulation } = req.body;
  if (!messages || !Array.isArray(messages)) {
    return res.status(400).json({ error: "messages array required" });
  }

  const system = `You are RegRadar's AI compliance advisor for India. 
You have web search — use it to give accurate, current answers.
Current regulation context: "${regulation?.title || "Indian regulatory matters"}" from ${regulation?.source || "Indian regulators"} dated ${regulation?.date || "recent"}.
Sector: ${regulation?.sector?.join(", ") || "General"}

Answer like a senior compliance consultant — concise, actionable, specific.
If you don't know something, search for it. Always cite your source.`;

  try {
    console.log(`[CHAT] User: ${messages[messages.length - 1]?.content?.slice(0, 60)}...`);
    const reply = await callClaudeChat(system, messages, 2000);
    res.json({ success: true, reply });
  } catch (err) {
    console.error("[CHAT ERROR]", err.message);
    res.status(500).json({ success: false, error: err.message });
  }
});

// ─── ROUTE: Serve frontend ────────────────────────────────────────────────────
app.get("*", (req, res) => {
  res.sendFile(path.join(__dirname, "public", "index.html"));
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`\n⚡ RegRadar running on http://localhost:${PORT}`);
  console.log(`   Model: ${MODEL}`);
  console.log(`   API Key: ${API_KEY.slice(0, 10)}...${API_KEY.slice(-4)}\n`);
});
