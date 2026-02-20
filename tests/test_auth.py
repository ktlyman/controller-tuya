"""Tests for the auth module (signing logic)."""

from tuya_agent.auth import TokenInfo, sign_request
from tuya_agent.config import TuyaConfig


def _config() -> TuyaConfig:
    return TuyaConfig(access_id="test_id", access_secret="test_secret", api_region="us")


class TestSignRequest:
    def test_returns_required_headers(self):
        cfg = _config()
        headers = sign_request(cfg, "GET", "/v1.0/token?grant_type=1", t=1000, nonce="abc")
        assert headers["client_id"] == "test_id"
        assert headers["sign_method"] == "HMAC-SHA256"
        assert headers["t"] == "1000"
        assert headers["nonce"] == "abc"
        assert "sign" in headers
        # No access_token header when token is empty.
        assert "access_token" not in headers

    def test_includes_access_token_when_provided(self):
        cfg = _config()
        headers = sign_request(
            cfg, "GET", "/v1.0/devices/123", access_token="tok_abc", t=2000, nonce="def"
        )
        assert headers["access_token"] == "tok_abc"

    def test_sign_is_deterministic(self):
        cfg = _config()
        h1 = sign_request(cfg, "GET", "/v1.0/token", t=5000, nonce="nonce1")
        h2 = sign_request(cfg, "GET", "/v1.0/token", t=5000, nonce="nonce1")
        assert h1["sign"] == h2["sign"]

    def test_sign_changes_with_method(self):
        cfg = _config()
        h_get = sign_request(cfg, "GET", "/v1.0/devices", t=5000, nonce="n")
        h_post = sign_request(cfg, "POST", "/v1.0/devices", t=5000, nonce="n")
        assert h_get["sign"] != h_post["sign"]

    def test_sign_changes_with_body(self):
        cfg = _config()
        h1 = sign_request(cfg, "POST", "/v1.0/devices", body="", t=5000, nonce="n")
        h2 = sign_request(cfg, "POST", "/v1.0/devices", body='{"a":1}', t=5000, nonce="n")
        assert h1["sign"] != h2["sign"]


class TestTokenInfo:
    def test_not_expired_when_fresh(self):
        token = TokenInfo(
            access_token="a", refresh_token="r", expire_time=7200
        )
        assert not token.is_expired

    def test_expired_when_past_lifetime(self):
        import time

        token = TokenInfo(
            access_token="a",
            refresh_token="r",
            expire_time=7200,
            acquired_at=time.time() - 8000,
        )
        assert token.is_expired
