import urllib.request

from quaestio.smoke_test import _SmokeRequestLimiter, _smoke_request_budget, _smoke_request_limit


def test_smoke_limit_is_capped_at_provider_quota(monkeypatch):
    monkeypatch.setenv("QUAESTIO_SMOKE_REQUESTS_PER_MINUTE", "999")
    assert _smoke_request_limit() == 40
    assert _SmokeRequestLimiter(999).max_requests == 40


def test_smoke_budget_restores_http_boundary():
    original = urllib.request.urlopen
    with _smoke_request_budget():
        assert urllib.request.urlopen is not original
    assert urllib.request.urlopen is original
