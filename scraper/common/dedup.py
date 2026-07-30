import hashlib


def make_job_fingerprint(source: str, source_job_id: str) -> str:
    """Stable unique key per job, independent of DB auto-increment ids.
    Using source + source's own listing id (not a hash of full content) so
    an edited job (e.g. deadline extended) still resolves to the same row."""
    raw = f"{source}:{source_job_id}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()
