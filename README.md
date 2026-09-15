# Kerala IT Park Job Aggregator

Aggregates job listings from Kerala's IT parks (Infopark, Technopark) into one searchable platform, with AI-generated summaries and direct apply-by-email links.

Built as a three-part system: a scraping pipeline that fills a database, a REST API that serves it, and a React frontend that consumes the API.

---

## Architecture

```
Infopark (static HTML) ─┐
                        ├─> Scraper ─> Supabase ─> Flask API ─> React frontend
Technopark (JS/SPA) ────┘
```

| Layer | Stack | Directory |
|---|---|---|
| Scraper | Python, BeautifulSoup, Playwright | `scraper/` |
| Database | Supabase (Postgres) | — |
| Backend API | Flask | `backend/` |
| Frontend | React + TypeScript + Vite + Tailwind | `frontend/` |

---

## The scraping pipeline

Runs in four stages. Each stage is independently re-runnable and resumes where it left off, so a failed or rate-limited run never has to start over.

### 1. Listing scrape
Pulls the job list (title, company, dates, detail URL) from each source.

- **Infopark** — static HTML table, paginated via `?page=N`. Plain `requests` + BeautifulSoup.
- **Technopark** — SPA with infinite scroll. Its `paginated-jobs` JSON endpoint returns 404 to plain HTTP requests even with matching headers/cookies/XSRF token (TLS-fingerprint anti-bot check), so this uses **Playwright** driving real Chromium, listening for the page's own XHR responses while scrolling.

Both stop dynamically — Infopark on the first empty page, Technopark after several scrolls with no new page. `MAX_PAGES` is a high safety ceiling (1000), not the real stopping condition, so future growth in listing size isn't silently truncated.

Results are deduplicated by fingerprint (`sha256(source + source_job_id)`) and upserted. Jobs present in the DB but absent from a fresh scrape get marked `expired`.

### 2. Detail backfill
For each job without a description, fetches its detail page and extracts:

- **Full description** — with nav/header/footer/breadcrumb chrome stripped out, then rebuilt block-by-block (one paragraph or list item per line, `•` bullets preserved) so it renders readably instead of as one run-on wall of text.
- **Contact email** — prefers an explicit `Contact Email:` labelled field, then a `mailto:` link, then a plain-text scan. Generic park addresses (`info@infopark.in`) are filtered out as noise.
- **Experience range** — regex extraction of `experience_min` / `experience_max` from phrasing like `5+ years`, `3-5 years`, `minimum 2 years`, `fresher`. Returns `(None, None)` rather than guessing when nothing matches.

A genuine 404 here means the posting was removed from the live site, so the job is marked `expired` instead of being retried forever.

### 3. AI summarization
Generates a 2-3 sentence `short_description` for each job (role, key skills, experience level).

Uses a **multi-provider fallback chain** — Groq → NVIDIA NIM → OpenRouter — because every free tier here is unreliable in a different way (rate limits, deprecated models, reasoning models returning empty content, timeouts). A sticky cursor skips providers already known to be exhausted within a run, with a 60s cooldown before retrying from the top.

Summaries can be backfilled separately (`backfill_summaries`) without re-fetching detail pages, for when the AI step fails but the scrape succeeded.

### 4. Cleanup
Deletes jobs that have been `expired` for more than a day. This is a hard delete — see the caveat below.

---

## Setup

### Prerequisites
- Python 3.12+
- Node.js 18+
- A Supabase project

### 1. Install dependencies

```bash
pip install -r requirements.txt
playwright install chromium          # required for the Technopark scraper
cd frontend && npm install && cd ..
```

### 2. Create the database table

Run in the Supabase SQL editor:

```sql
create table jobs (
    id bigint generated always as identity primary key,
    fingerprint text unique not null,
    source text not null,
    source_job_id text not null,
    job_title text not null,
    company text not null,
    posted_date text,
    closing_date text,
    detail_url text,
    description text,
    contact_email text,
    short_description text,
    experience_min int,
    experience_max int,
    status text not null default 'active',
    expired_at timestamptz,
    last_seen_at timestamptz not null default now(),
    created_at timestamptz not null default now()
);
```

If the table already exists from an earlier version:

```sql
alter table jobs add column if not exists description text;
alter table jobs add column if not exists contact_email text;
alter table jobs add column if not exists short_description text;
alter table jobs add column if not exists expired_at timestamptz;
alter table jobs add column if not exists experience_min int;
alter table jobs add column if not exists experience_max int;
```

### 3. Configure environment

Copy `.env.example` to `.env` and fill in:

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-secret-key       # server-side key, never expose to frontend
GROQ_API_KEY=
NVIDIA_API_KEY=
OPENROUTER_API_KEY=
LOG_LEVEL=INFO
```

At least one AI key is needed for summaries; the rest of the pipeline works without any.

Frontend config — `frontend/.env`:

```
VITE_API_BASE_URL=http://localhost:5000
```

---

## Running

### Everything, in order

```bash
python -m scraper.run_all
```

Runs scrape → detail backfill → summary backfill → cleanup for both sources. Each step is isolated: a failure in one is logged and the pipeline continues to the next.

To keep it running on a schedule without cron:

```bash
python -m scraper.run_all --forever                      # every 3 days
python -m scraper.run_all --forever --interval-days 4
```

### Individual steps

```bash
python -m scraper.scheduler                        # listing scrape, both sources
python -m scraper.infopark.scraper                 # one source's listing scrape
python -m scraper.technopark.scraper

python -m scraper.infopark.backfill_details        # detail pages + email + experience
python -m scraper.technopark.backfill_details

python -m scraper.infopark.backfill_summaries      # AI summaries only, no re-fetch
python -m scraper.technopark.backfill_summaries

python -m scraper.cleanup_expired --days 1         # hard-delete old expired jobs
python -m scraper.reset_descriptions --source all  # one-off, see below
```

### Backend + frontend

```bash
python -m backend.app        # http://localhost:5000
cd frontend && npm run dev   # http://localhost:5173
```

Both need to be running for the frontend to show data.

### Tests

```bash
pytest -v
```

All tests run offline against fixtures and mocks — no live network calls, no dependency on the source sites being up.

---

## API

| Endpoint | Description |
|---|---|
| `GET /health` | Health check |
| `GET /api/jobs` | List jobs. Params: `search`, `source`, `page`, `limit` (max 100) |
| `GET /api/jobs/<id>` | Single job detail |

Every query filters `status = 'active'` — expired jobs never surface.

---

## Security and compliance notes

- **robots.txt checked** for both sources; neither disallows the paths scraped.
- **Host allow-list** — the HTTP client refuses any host not explicitly listed, including look-alike domains (`infopark.in.evil.com`). This is enforced in code, not convention.
- **Rate limiting** — randomized 2-4s delay between requests, for politeness and to avoid bans.
- **Browser User-Agent** — used deliberately, not to disguise the scraper, but because Technopark's detail-page route 404s a bot-identifying UA regardless of what robots.txt permits.
- **No secrets in code** — all credentials come from `.env`, never logged.
- **Service key is server-side only** — never exposed to the frontend.
- The frontend carries a disclaimer that this is an unaffiliated aggregator, with attribution links back to the original postings.

---

## Things worth knowing before you change anything

**Cleanup is a hard delete.** `cleanup_expired` permanently removes rows. If a user's application history ever references a job, that reference breaks. Expired rows cost negligible storage — think carefully before running this aggressively.

**`reset_descriptions` is one-off, not routine.** It nulls `description` for active jobs so the next detail backfill re-fetches them with current extraction logic. Run it once after improving the extractor; running it repeatedly just re-hits the source sites for nothing.

**Free AI tiers rotate constantly.** Groq deprecated two models mid-project; OpenRouter delisted two free model IDs. If summaries start failing, check the provider's current model list before debugging the code — the model name in `config.py` is the most likely culprit.

**Experience extraction is regex, not AI.** It's fast and free and handles the common phrasings, but it will miss unusual ones and returns `(None, None)` rather than guessing. If the miss rate turns out to be high in practice, the upgrade path is to piggyback structured extraction onto the existing AI summarization call.

**Description formatting is heuristic.** The scraper preserves block structure, and the frontend reconstructs sections from known heading keywords. Every company writes postings differently — this won't be perfect for every one, and that's expected.

---

## Not built yet

- User accounts / auth (Supabase Auth)
- User profiles (resume upload, GitHub, portfolio)
- ATS-style CV tailoring per job
- Fit-score matching
- Application tracking
- Cyberpark as a third source (deferred: its postings mix email, external forms, and walk-ins, so apply-method detection is needed first)