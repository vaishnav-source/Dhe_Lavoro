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
INFOPARK_MAX_PAGES = 1000  # safety ceiling only — real stop is an empty page
# (see infopark/scraper.py). Set high on purpose: if Infopark's listing
# grows past today's ~24 pages, the scraper must keep following it rather
# than silently truncating at a number that made sense today.

TECHNOPARK_LANDING_URL = "https://technopark.in/job-search?search=&type=Job"
TECHNOPARK_PAGINATED_URL = "https://technopark.in/paginated-jobs"
TECHNOPARK_MAX_PAGES = 1000  # safety ceiling only — real stop is a run of
# stagnant scrolls with no new page (see technopark/scraper.py). Same
# reasoning as INFOPARK_MAX_PAGES: don't hardcode today's page count as a
# future limit.
TECHNOPARK_DETAIL_URL_TEMPLATE = "https://technopark.in/job-details/{job_id}?job={title}"

# --- Networking ---
REQUEST_TIMEOUT_SECONDS = 10
# NOTE: using a real browser User-Agent, not an honest bot string. Both
# Infopark and Technopark's robots.txt explicitly allow scraping the paths
# we hit (checked and documented in the PRD) — this isn't bypassing
# consent, it's avoiding a UA-fingerprint-based anti-bot block that
# Technopark's detail-page route applies regardless of robots.txt.
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
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")  # llama-3.1-8b-instant
# and llama-3.3-70b-versatile were deprecated Aug 16, 2026 — gpt-oss-20b is
# current as of this writing, but Groq's free-tier model lineup has
# rotated multiple times already; re-check console.groq.com/docs/models
# if this starts erroring again.
# gpt-oss-20b is a REASONING model — it spends tokens on internal
# chain-of-thought before producing the final answer, separate from the
# max_tokens budget for visible output. Too low a max_tokens value here
# means it can burn the whole budget reasoning and never emit visible
# content, leaving message.content null (this happened at 200).
GROQ_MAX_TOKENS = 800  # openai/gpt-oss-20b (a reasoning model) sometimes
# consumes most of the token budget on internal reasoning before writing
# the final answer into `content` — a known, currently-unresolved Groq
# bug with gpt-oss models (confirmed on Groq's community forum, not
# specific to this project). Extra headroom here reduces how often it
# happens; our multi-provider fallback (NVIDIA NIM next in chain) covers
# it regardless when it does.
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "meta/llama-3.3-70b-instruct")
NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

HF_API_KEY = os.getenv("HF_API_KEY", "")
HF_MODEL = os.getenv("HF_MODEL", "meta-llama/Llama-3.1-8B-Instruct")
HF_API_URL = f"https://router.huggingface.co/hf-inference/models/{HF_MODEL}"

AI_TIMEOUT_SECONDS = 45  # was 30 — NVIDIA NIM's free tier can be slow
# under load and hit that ceiling on legitimate (if slow) responses, not
# just genuine hangs. Extra margin here trades a bit of worst-case wait
# time for fewer false-timeout failures that push the whole chain into
# its 60s cooldown unnecessarily.
AI_MAX_INPUT_CHARS = 1500

# --- Logging ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")