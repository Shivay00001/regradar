"""
RegRadar — AI Provider Abstraction
Supports Ollama (free/local), Groq (free cloud), Google Gemini (free cloud).
"""

import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

# ─── Config ─────────────────────────────────────────────────────────────────────

def get_provider_config():
    """Detect and return the active AI provider configuration."""
    provider = os.getenv("AI_PROVIDER", "ollama").lower().strip()

    configs = {
        "ollama": {
            "name": "ollama",
            "model": os.getenv("OLLAMA_MODEL", "llama3"),
            "url": os.getenv("OLLAMA_URL", "http://localhost:11434"),
            "api_key": None,
            "display": "Ollama (Local)",
        },
        "groq": {
            "name": "groq",
            "model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            "url": "https://api.groq.com/openai/v1/chat/completions",
            "api_key": os.getenv("GROQ_API_KEY", ""),
            "display": "Groq Cloud",
        },
        "gemini": {
            "name": "gemini",
            "model": os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
            "url": "https://generativelanguage.googleapis.com/v1beta",
            "api_key": os.getenv("GEMINI_API_KEY", ""),
            "display": "Google Gemini",
        },
    }

    config = configs.get(provider, configs["ollama"])
    return config


# ─── Ollama Provider ────────────────────────────────────────────────────────────

def call_ollama(system_prompt, user_message, max_tokens=4096, config=None):
    """Call local Ollama instance."""
    if not config:
        config = get_provider_config()

    url = f"{config['url']}/api/chat"

    payload = {
        "model": config["model"],
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "stream": False,
        "options": {
            "num_predict": max_tokens,
            "temperature": 0.3,
        },
    }

    try:
        resp = requests.post(url, json=payload, timeout=600)
        resp.raise_for_status()
        data = resp.json()
        return data.get("message", {}).get("content", "")
    except requests.exceptions.ConnectionError:
        raise ConnectionError(
            f"Cannot connect to Ollama at {config['url']}. "
            "Make sure Ollama is running (ollama serve) and you have a model pulled (ollama pull llama3)."
        )
    except Exception as e:
        raise RuntimeError(f"Ollama error: {e}")


def call_ollama_chat(system_prompt, messages, max_tokens=2048, config=None):
    """Call Ollama with multi-turn chat."""
    if not config:
        config = get_provider_config()

    url = f"{config['url']}/api/chat"

    ollama_messages = [{"role": "system", "content": system_prompt}]
    for m in messages:
        ollama_messages.append({"role": m["role"], "content": m["content"]})

    payload = {
        "model": config["model"],
        "messages": ollama_messages,
        "stream": False,
        "options": {
            "num_predict": max_tokens,
            "temperature": 0.3,
        },
    }

    try:
        resp = requests.post(url, json=payload, timeout=600)
        resp.raise_for_status()
        data = resp.json()
        return data.get("message", {}).get("content", "")
    except requests.exceptions.ConnectionError:
        raise ConnectionError(f"Cannot connect to Ollama at {config['url']}.")
    except Exception as e:
        raise RuntimeError(f"Ollama chat error: {e}")


# ─── Groq Provider ──────────────────────────────────────────────────────────────

def call_groq(system_prompt, user_message, max_tokens=4096, config=None):
    """Call Groq cloud API (OpenAI-compatible)."""
    if not config:
        config = get_provider_config()

    if not config.get("api_key"):
        raise ValueError("GROQ_API_KEY not set in .env file. Get a free key at console.groq.com")

    payload = {
        "model": config["model"],
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.3,
    }

    resp = requests.post(
        config["url"],
        headers={
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=60,
    )

    if not resp.ok:
        raise RuntimeError(f"Groq API error {resp.status_code}: {resp.text[:200]}")

    data = resp.json()
    return data["choices"][0]["message"]["content"]


def call_groq_chat(system_prompt, messages, max_tokens=2048, config=None):
    """Call Groq with multi-turn chat."""
    if not config:
        config = get_provider_config()

    if not config.get("api_key"):
        raise ValueError("GROQ_API_KEY not set.")

    groq_messages = [{"role": "system", "content": system_prompt}]
    for m in messages:
        groq_messages.append({"role": m["role"], "content": m["content"]})

    payload = {
        "model": config["model"],
        "messages": groq_messages,
        "max_tokens": max_tokens,
        "temperature": 0.3,
    }

    resp = requests.post(
        config["url"],
        headers={
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=60,
    )

    if not resp.ok:
        raise RuntimeError(f"Groq API error {resp.status_code}: {resp.text[:200]}")

    data = resp.json()
    return data["choices"][0]["message"]["content"]


# ─── Gemini Provider ────────────────────────────────────────────────────────────

def call_gemini(system_prompt, user_message, max_tokens=4096, config=None):
    """Call Google Gemini API."""
    if not config:
        config = get_provider_config()

    if not config.get("api_key"):
        raise ValueError("GEMINI_API_KEY not set in .env file. Get a free key at aistudio.google.com")

    url = f"{config['url']}/models/{config['model']}:generateContent?key={config['api_key']}"

    payload = {
        "system_instruction": {
            "parts": [{"text": system_prompt}]
        },
        "contents": [
            {
                "role": "user",
                "parts": [{"text": user_message}]
            }
        ],
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": 0.3,
        },
    }

    resp = requests.post(
        url,
        headers={"Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )

    if not resp.ok:
        raise RuntimeError(f"Gemini API error {resp.status_code}: {resp.text[:200]}")

    data = resp.json()
    candidates = data.get("candidates", [])
    if candidates:
        parts = candidates[0].get("content", {}).get("parts", [])
        return "".join(p.get("text", "") for p in parts)
    return ""


def call_gemini_chat(system_prompt, messages, max_tokens=2048, config=None):
    """Call Gemini with multi-turn chat."""
    if not config:
        config = get_provider_config()

    if not config.get("api_key"):
        raise ValueError("GEMINI_API_KEY not set.")

    url = f"{config['url']}/models/{config['model']}:generateContent?key={config['api_key']}"

    contents = []
    for m in messages:
        role = "user" if m["role"] == "user" else "model"
        contents.append({
            "role": role,
            "parts": [{"text": m["content"]}]
        })

    payload = {
        "system_instruction": {
            "parts": [{"text": system_prompt}]
        },
        "contents": contents,
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": 0.3,
        },
    }

    resp = requests.post(
        url,
        headers={"Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )

    if not resp.ok:
        raise RuntimeError(f"Gemini API error {resp.status_code}: {resp.text[:200]}")

    data = resp.json()
    candidates = data.get("candidates", [])
    if candidates:
        parts = candidates[0].get("content", {}).get("parts", [])
        return "".join(p.get("text", "") for p in parts)
    return ""


# ─── Unified Interface ──────────────────────────────────────────────────────────

PROVIDERS = {
    "ollama": {"call": call_ollama, "chat": call_ollama_chat},
    "groq": {"call": call_groq, "chat": call_groq_chat},
    "gemini": {"call": call_gemini, "chat": call_gemini_chat},
}


def call_ai(system_prompt, user_message, max_tokens=4096):
    """Unified AI call — routes to the configured provider."""
    config = get_provider_config()
    provider = config["name"]
    fn = PROVIDERS[provider]["call"]
    return fn(system_prompt, user_message, max_tokens, config)


def call_ai_chat(system_prompt, messages, max_tokens=2048):
    """Unified multi-turn AI chat — routes to the configured provider."""
    config = get_provider_config()
    provider = config["name"]
    fn = PROVIDERS[provider]["chat"]
    return fn(system_prompt, messages, max_tokens, config)


def check_provider_health():
    """Check if the configured AI provider is reachable."""
    config = get_provider_config()

    if config["name"] == "ollama":
        try:
            resp = requests.get(f"{config['url']}/api/tags", timeout=5)
            if resp.ok:
                models = [m["name"] for m in resp.json().get("models", [])]
                return {
                    "status": "connected",
                    "provider": config["display"],
                    "model": config["model"],
                    "available_models": models,
                }
        except:
            pass
        return {
            "status": "disconnected",
            "provider": config["display"],
            "model": config["model"],
            "error": "Ollama not running. Start with: ollama serve",
        }

    elif config["name"] == "groq":
        if config.get("api_key"):
            return {
                "status": "configured",
                "provider": config["display"],
                "model": config["model"],
            }
        return {
            "status": "no_key",
            "provider": config["display"],
            "error": "Set GROQ_API_KEY in .env",
        }

    elif config["name"] == "gemini":
        if config.get("api_key"):
            return {
                "status": "configured",
                "provider": config["display"],
                "model": config["model"],
            }
        return {
            "status": "no_key",
            "provider": config["display"],
            "error": "Set GEMINI_API_KEY in .env",
        }

    return {"status": "unknown", "provider": config.get("display", "Unknown")}
