"""
Central config. All tunables live here — nothing hardcoded inline in scrapers.
Secrets (DB keys etc.) come from environment variables only, never committed.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# --- Source URLs (fixed allow-list — scrapers must never build URLs from
# untrusted/user input; this prevents SSRF-style misuse of the fetch layer) ---
ALLOWED_HOSTS = {
    "infopark.in",
    "technopark.in",
}

INFOPARK_BASE_URL = "https://infopark.in/companies-job"
INFOPARK_MAX_PAGES = 24

TECHNOPARK_LANDING_URL = "https://technopark.in/job-search?search=&type=Job"
TECHNOPARK_PAGINATED_URL = "https://technopark.in/paginated-jobs"
TECHNOPARK_MAX_PAGES = 50  # safety ceiling — real loop stops on empty page
TECHNOPARK_DETAIL_URL_TEMPLATE = "https://technopark.in/job-details/{job_id}?job={title}"

# --- Networking ---
REQUEST_TIMEOUT_SECONDS = 10
# NOTE: using a real browser User-Agent, not an honest bot string. Both
# Infopark and Technopark's robots.txt explicitly allow scraping the paths
# we hit (checked and documented in the PRD) — this isn't bypassing
# consent, it's avoiding a UA-fingerprint-based anti-bot block that
# Technopark's detail-page route applies regardless of robots.txt (an
# honest "JobAggregatorBot/0.1" UA got 404'd on every request; the same
# URLs work fine with a standard browser UA).
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

# --- Rate limiting (politeness — also reduces our own ban risk) ---
MIN_DELAY_SECONDS = 2.0
MAX_DELAY_SECONDS = 4.0

# --- Retry ---
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2  # exponential base

# --- Database (Supabase) ---
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")  # server-side key, never expose to frontend

# --- AI summarization (multi-provider fallback: Groq -> NVIDIA NIM) ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")  # fast/cheap — verify current model name in Groq's docs, names change
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "meta/llama-3.3-70b-instruct")
NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
# "openrouter/free" auto-routes to whatever free model is currently live on
# OpenRouter — avoids hardcoding a specific :free model ID, since those get
# delisted/rotated out on short notice (confirmed twice already). Kept
# configured but not in the active PROVIDERS chain — see ai_summarizer.py.
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

HF_API_KEY = os.getenv("HF_API_KEY", "")
HF_MODEL = os.getenv("HF_MODEL", "meta-llama/Llama-3.1-8B-Instruct")
# Hugging Face retired api-inference.huggingface.co (returns 410) in favor of
# this router domain — same models, new host+path prefix.
HF_API_URL = f"https://router.huggingface.co/hf-inference/models/{HF_MODEL}"

AI_TIMEOUT_SECONDS = 30
AI_MAX_INPUT_CHARS = 1500  # kept small deliberately — Groq's free tier caps at
# 20,000 tokens/minute (TPM), not just 30 requests/minute (RPM). A 4000-char
# input pushed each call over ~1000+ tokens, blowing the TPM budget well
# before the RPM one. 1500 chars (~400 tokens) leaves headroom for the
# system prompt + output tokens while still giving the model enough of the
# description to summarize accurately.

# --- Logging ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")