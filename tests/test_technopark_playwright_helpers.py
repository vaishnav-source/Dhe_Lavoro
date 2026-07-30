from scraper.technopark.scraper import _page_number_from_url


def test_extracts_page_number_from_normal_url():
    url = "https://technopark.in/paginated-jobs?page=3&search=&type=Job"
    assert _page_number_from_url(url) == 3


def test_returns_none_when_page_param_missing():
    url = "https://technopark.in/paginated-jobs?search=&type=Job"
    assert _page_number_from_url(url) is None


def test_returns_none_for_non_numeric_page():
    url = "https://technopark.in/paginated-jobs?page=abc"
    assert _page_number_from_url(url) is None


def test_returns_none_for_unrelated_url():
    url = "https://technopark.in/some-other-endpoint"
    assert _page_number_from_url(url) is None
