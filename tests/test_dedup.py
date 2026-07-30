from scraper.common.dedup import make_job_fingerprint


def test_same_input_gives_same_fingerprint():
    a = make_job_fingerprint("infopark", "24887")
    b = make_job_fingerprint("infopark", "24887")
    assert a == b


def test_different_source_job_id_gives_different_fingerprint():
    a = make_job_fingerprint("infopark", "24887")
    b = make_job_fingerprint("infopark", "24888")
    assert a != b


def test_different_source_same_job_id_gives_different_fingerprint():
    a = make_job_fingerprint("infopark", "1")
    b = make_job_fingerprint("technopark", "1")
    assert a != b
