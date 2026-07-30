# Job Aggregator — Scraper Module

## What's implemented (Levels 1–4 from the learning roadmap)

| Level | Concept | Where |
|---|---|---|
| 1 | Static HTML scraping (requests + BeautifulSoup) | `scraper/infopark/parser.py`, `scraper.py` |
| 2 | Session handling (foundation laid, Technopark impl next) | `scraper/common/http_client.py` (`safe_get`/`safe_post` accept a shared `requests.Session`) |
| 4 | Retry w/ exponential backoff | `tenacity` decorators in `http_client.py` |
| 4 | Rate limiting / politeness | `scraper/common/rate_limiter.py` |
| 4 | Structured logging (no secrets logged) | `scraper/common/logger.py` |
| 4 | Error isolation (one bad page ≠ whole run fails) | `scraper/infopark/scraper.py` — try/except per page |
| — | Dedup fingerprinting | `scraper/common/dedup.py` |

Technopark (Level 2/3: session+XSRF or Playwright) and Cyberpark (Phase 2) are not yet implemented — this pass focused on getting the pattern and safety rails right on Infopark first, so the same pattern reproduces cleanly.

## Security measures

- **Host allow-list (SSRF guard)** — `http_client.py` refuses to fetch any host not explicitly in `config.ALLOWED_HOSTS`, including look-alike domains (`infopark.in.evil.com`). Covered by `tests/test_http_client_security.py`.
- **No secrets in code** — DB keys loaded from `.env` (see `.env.example`), never hardcoded, never logged.
- **Honest User-Agent** — identifies the bot rather than spoofing a browser, per the risk-reduction plan in the PRD.
- **Timeouts on every request** — no request can hang indefinitely.
- **Retry with backoff, capped attempts** — avoids hammering the source on transient failures.
- **Randomized delay between requests** — politeness + reduces ban risk.
- **Input validation before storage** — parser skips rows missing required fields instead of writing partial/garbage rows.
- **robots.txt compliance** — confirmed manually for Infopark/Technopark (see PRD); scraper does not access any disallowed path.

## Testing

Run:
```
pip install -r requirements.txt
pytest -v
```

- `test_infopark_parser.py` — parser correctness against a static fixture (`tests/fixtures/infopark_sample.html`), including a malformed-row case, so a future site redesign that breaks parsing fails a test instead of silently returning bad data.
- `test_dedup.py` — fingerprint stability/uniqueness.
- `test_http_client_security.py` — the SSRF/allow-list guard, including the look-alike-domain case.

Tests run entirely offline against fixtures/mocks — no live network calls, so CI doesn't depend on the target sites being up or on rate-limit budget.

## Not yet done (flag before production)
- Re-verify Infopark's actual table markup against live `view-source` (parser was built from a markdown-rendered fetch, not raw HTML — column order assumed stable, should be double-checked once you can inspect raw HTML/class names directly).
- Cyberpark scraper (Phase 2, per PRD — apply-method detection needed).
- Backend API / frontend (not started).

## Scheduler (`scraper/scheduler.py`)
- `run_once()` — runs every configured source (currently Infopark, Technopark) sequentially: scrape → `upsert_jobs()` → `mark_stale_jobs_expired()`. Add Cyberpark later by appending one entry to `SOURCES` — the run loop doesn't change.
- Per-source failure isolation — if one source's scraper or DB call throws, it's caught and logged; other sources still run. Exit code is non-zero only if *every* source failed, so cron/monitoring can alert on total failure without false-alarming on a single flaky source.
- Two invocation modes: `python -m scraper.scheduler` (single run — pair with cron) or `python -m scraper.scheduler --forever` (in-process loop with a sleep interval, if you'd rather run one long-lived process than rely on system cron).
- Example crontab line is in the file's module docstring.

## Database writer (`scraper/common/db_writer.py`)
- `upsert_jobs()` — writes normalized job dicts into Supabase `jobs` table, batched (default 200/batch), keyed on `fingerprint` (unique constraint) so re-scrapes update instead of duplicate.
- `mark_stale_jobs_expired()` — after a full scrape run, flips any job still `active` for that source but missing from the run's results to `expired` (handles listings pulled before their stated deadline). Refuses to run if given an empty fingerprint list (safety guard against wiping a whole source's active status by accident).
- Table schema (SQL) documented at the top of `db_writer.py` — run it in the Supabase SQL editor before first use.
- Both functions accept an injected `client` — this is what makes them unit-testable (`tests/test_db_writer.py`) without hitting real Supabase.
