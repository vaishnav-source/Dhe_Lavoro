"""
Job listing endpoints — GET /api/jobs (search/filter/paginate) and
GET /api/jobs/<id> (single job detail).

Every query filters status='active' — expired jobs (see scraper's
mark_job_expired / mark_stale_jobs_expired / delete_expired_jobs) must
never surface here, per the PRD data-lifecycle rule.
"""
from flask import Blueprint, request, jsonify

from scraper.common.db import get_client
from scraper.common.logger import get_logger

log = get_logger(__name__)

jobs_bp = Blueprint("jobs", __name__)

DEFAULT_LIMIT = 20
MAX_LIMIT = 100

# The two sources this site aggregates. An unfiltered "All Parks" request
# interleaves them (see _interleaved_plan) rather than running a single
# ORDER BY id DESC query across the combined table, which would be
# dominated by whichever source happens to have higher recent IDs (e.g.
# if it was scraped more recently) instead of actually mixing both parks.
SOURCES = ["infopark", "technopark"]


def _parse_int_param(name: str):
    """Reads an optional int query param, silently ignoring it if it's
    missing or not a valid int — an unparseable exp_min/exp_max shouldn't
    500 the whole request, it should just not filter on it."""
    raw = request.args.get(name)
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _parse_pagination():
    """Reads page/limit query params with sane bounds — never trust raw
    client input directly into a DB range() call."""
    try:
        page = int(request.args.get("page", 1))
    except ValueError:
        page = 1
    try:
        limit = int(request.args.get("limit", DEFAULT_LIMIT))
    except ValueError:
        limit = DEFAULT_LIMIT

    page = max(page, 1)
    limit = min(max(limit, 1), MAX_LIMIT)
    return page, limit


def _apply_search_and_experience_filters(query, search, exp_min, exp_max):
    """Filters shared by every jobs query regardless of source scope."""
    if search:
        # matches job title OR company, case-insensitive
        escaped = search.replace(",", "")  # commas break the or_() filter syntax
        query = query.or_(f"job_title.ilike.%{escaped}%,company.ilike.%{escaped}%")
    if exp_min is not None or exp_max is not None:
        # Range-overlap filter against experience_min/experience_max
        # (nullable — regex extraction doesn't catch every posting).
        # A job with no extracted range at all can't be matched either
        # way, so it's excluded rather than silently included.
        query = query.not_.is_("experience_min", "null")
        if exp_min is not None:
            # job's upper bound must reach exp_min — a null experience_max
            # means "X+ years", i.e. open-ended, so it always qualifies
            query = query.or_(f"experience_max.gte.{exp_min},experience_max.is.null")
        if exp_max is not None:
            query = query.lte("experience_min", exp_max)
    return query


def _base_query(db, source, search, exp_min, exp_max, columns, **select_kwargs):
    """Active jobs for one source with the shared search/experience filters."""
    query = (
        db.table("jobs")
        .select(columns, **select_kwargs)
        .eq("status", "active")
        .eq("source", source)
    )
    return _apply_search_and_experience_filters(query, search, exp_min, exp_max)


def _count_matching(db, source, search, exp_min, exp_max):
    """How many active jobs match for one source. Needed up front so we
    never ask PostgREST for a range past the end of a source's rows —
    that returns HTTP 416 and used to surface as a 500 on later pages."""
    query = _base_query(db, source, search, exp_min, exp_max, "id", count="exact")
    return query.limit(1).execute().count or 0


def _fetch_slice(db, source, search, exp_min, exp_max, start, end):
    """Rows start..end (inclusive) of one source, newest first."""
    query = _base_query(db, source, search, exp_min, exp_max, "*")
    return query.order("id", desc=True).range(start, end).execute().data or []


def _interleaved_plan(counts, offset, limit):
    """Which (source, row_index_within_source) sits at each position of the
    combined "All Parks" list, for positions offset..offset+limit-1.

    The combined list alternates sources (infopark, technopark, infopark,
    ...) while both still have rows, then continues with whatever is left
    of the larger source. Page size therefore stays full to the very last
    page, total pages = ceil(total / limit), and every job is reachable —
    even when one park has far fewer jobs than the other."""
    a, b = SOURCES
    shorter_len = min(counts[a], counts[b])
    longer = a if counts[a] >= counts[b] else b
    total = counts[a] + counts[b]

    plan = []
    for pos in range(offset, min(offset + limit, total)):
        if pos < 2 * shorter_len:
            plan.append((SOURCES[pos % 2], pos // 2))
        else:
            plan.append((longer, shorter_len + (pos - 2 * shorter_len)))
    return plan


def _list_all_parks(db, search, exp_min, exp_max, page, limit):
    counts = {
        src: _count_matching(db, src, search, exp_min, exp_max) for src in SOURCES
    }
    total = sum(counts.values())
    plan = _interleaved_plan(counts, (page - 1) * limit, limit)

    # Each source's needed rows are consecutive, so one range query each.
    wanted = {}
    for src, idx in plan:
        low, high = wanted.get(src, (idx, idx))
        wanted[src] = (min(low, idx), max(high, idx))

    rows = {}
    for src, (low, high) in wanted.items():
        rows[src] = (low, _fetch_slice(db, src, search, exp_min, exp_max, low, high))

    jobs = []
    for src, idx in plan:
        low, data = rows[src]
        if 0 <= idx - low < len(data):  # guard: rows can change between queries
            jobs.append(data[idx - low])
    return jobs, total


def _list_single_source(db, source, search, exp_min, exp_max, page, limit):
    total = _count_matching(db, source, search, exp_min, exp_max)
    offset = (page - 1) * limit
    if offset >= total:  # page past the end: empty page, not an error
        return [], total
    jobs = _fetch_slice(db, source, search, exp_min, exp_max, offset, offset + limit - 1)
    return jobs, total


@jobs_bp.route("/jobs", methods=["GET"])
def list_jobs():
    db = get_client()

    search = request.args.get("search", "").strip()
    source = request.args.get("source", "").strip()
    exp_min = _parse_int_param("exp_min")
    exp_max = _parse_int_param("exp_max")
    page, limit = _parse_pagination()

    try:
        if source:
            jobs, total = _list_single_source(
                db, source, search, exp_min, exp_max, page, limit
            )
        else:
            jobs, total = _list_all_parks(db, search, exp_min, exp_max, page, limit)
    except Exception as exc:  # noqa: BLE001
        log.error("list_jobs query failed: %s", exc)
        return jsonify({"error": "failed to fetch jobs"}), 500

    return jsonify({
        "jobs": jobs,
        "total": total,
        "page": page,
        "limit": limit,
    })


@jobs_bp.route("/jobs/<int:job_id>", methods=["GET"])
def get_job(job_id):
    db = get_client()

    try:
        result = (
            db.table("jobs")
            .select("*")
            .eq("id", job_id)
            .eq("status", "active")
            .execute()
        )
    except Exception as exc:  # noqa: BLE001
        log.error("get_job query failed for id=%s: %s", job_id, exc)
        return jsonify({"error": "failed to fetch job"}), 500

    rows = result.data or []
    if not rows:
        return jsonify({"error": "job not found"}), 404

    return jsonify(rows[0])