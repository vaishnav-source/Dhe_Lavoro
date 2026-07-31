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

# --- Networking ---
REQUEST_TIMEOUT_SECONDS = 10
USER_AGENT = (
    "Mozilla/5.0 (compatible; JobAggregatorBot/0.1; "
    "+https://example.com/about-bot)"  # identify honestly, replace w/ real contact URL later
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

# --- AI summarization (Groq) ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")  # fast/cheap — verify current model name in Groq's docs, names change
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_TIMEOUT_SECONDS = 15
GROQ_MAX_INPUT_CHARS = 4000  # cap description length sent to the model

# --- Logging ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
