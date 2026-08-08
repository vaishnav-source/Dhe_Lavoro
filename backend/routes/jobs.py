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


@jobs_bp.route("/jobs", methods=["GET"])
def list_jobs():
    db = get_client()

    search = request.args.get("search", "").strip()
    source = request.args.get("source", "").strip()
    page, limit = _parse_pagination()
    offset = (page - 1) * limit

    query = db.table("jobs").select("*", count="exact").eq("status", "active")

    if source:
        query = query.eq("source", source)
    if search:
        # matches job title OR company, case-insensitive
        escaped = search.replace(",", "")  # commas break the or_() filter syntax
        query = query.or_(f"job_title.ilike.%{escaped}%,company.ilike.%{escaped}%")

    query = query.order("id", desc=True).range(offset, offset + limit - 1)

    try:
        result = query.execute()
    except Exception as exc:  # noqa: BLE001
        log.error("list_jobs query failed: %s", exc)
        return jsonify({"error": "failed to fetch jobs"}), 500

    return jsonify({
        "jobs": result.data or [],
        "total": result.count if result.count is not None else len(result.data or []),
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