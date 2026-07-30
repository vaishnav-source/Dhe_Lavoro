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
- Technopark scraper (session + XSRF token handling, per PRD).
- DB writer (`common/db_writer.py`) — Supabase upsert logic, not yet built.
- Scheduler entrypoint (cron/APScheduler).
