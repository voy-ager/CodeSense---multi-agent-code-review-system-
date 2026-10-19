# tests/test_api_security.py — run: python -m unittest discover tests

import os
import unittest
from unittest.mock import patch

# Keep rate-limit counters in memory so tests don't depend on a local Redis.
os.environ["REDIS_URL"] = "memory://"

from fastapi.testclient import TestClient

from api.server import app, limiter
from tools.github import canonical_pr_url

# No `with` block: lifespan (graph compile, DB pool) isn't needed for these checks.
client = TestClient(app)


class PrUrlValidationTests(unittest.TestCase):
    def test_accepts_and_canonicalises(self):
        for url in [
            "https://github.com/psf/requests/pull/6746",
            "https://github.com/psf/requests/pull/6746/",
            "https://github.com/psf/requests/pull/6746/files",
            "https://github.com/psf/requests/pull/6746/files?w=1#diff-abc",
            "  https://github.com/psf/requests/pull/6746  ",
        ]:
            self.assertEqual(canonical_pr_url(url), "https://github.com/psf/requests/pull/6746", url)

    def test_rejects(self):
        for url in [
            "https://evil.com/psf/requests/pull/1",
            "http://github.com/psf/requests/pull/1",
            "https://github.com.evil.com/psf/requests/pull/1",
            "https://github.com/psf/requests/issues/1",
            "https://github.com/psf/../pull/1",
            "https://github.com/../requests/pull/1",
            "https://github.com/psf/requests/pull/abc",
            "https://github.com/psf/requests/pull/1/../../../user",
        ]:
            self.assertIsNone(canonical_pr_url(url), url)


class HardeningTests(unittest.TestCase):
    def setUp(self):
        limiter.reset()

    def test_invalid_url_is_400_with_security_headers(self):
        r = client.post("/review", json={"pr_url": "https://evil.com/pull/1"})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.headers["x-content-type-options"], "nosniff")
        self.assertEqual(r.headers["x-frame-options"], "DENY")
        self.assertIn("default-src 'none'", r.headers["content-security-policy"])

    def test_oversized_body_is_413(self):
        r = client.post("/review", content=b"x", headers={"Content-Length": "2000000", "Content-Type": "application/json"})
        self.assertEqual(r.status_code, 413)

    def test_overlong_pr_url_is_422(self):
        r = client.post("/review", json={"pr_url": "https://github.com/" + "a" * 600})
        self.assertEqual(r.status_code, 422)

    def test_rate_limit_on_review(self):
        codes = [client.post("/review", json={"pr_url": "bad"}).status_code for _ in range(11)]
        self.assertEqual(codes[:10], [400] * 10)
        self.assertEqual(codes[10], 429)

    def test_admin_endpoints_need_api_key(self):
        with patch.dict(os.environ, {"ADMIN_API_KEY": "s3cret"}):
            self.assertEqual(client.get("/reviews/stats").status_code, 401)
            self.assertEqual(client.get("/reviews/stats", headers={"X-API-Key": "wrong"}).status_code, 401)
            with patch("api.server.get_stats", return_value={"total_reviews": 0}):
                self.assertEqual(client.get("/reviews/stats", headers={"X-API-Key": "s3cret"}).status_code, 200)

    def test_admin_endpoints_locked_when_key_unset(self):
        with patch.dict(os.environ, {"ADMIN_API_KEY": ""}):
            self.assertEqual(client.get("/reviews/recent", headers={"X-API-Key": ""}).status_code, 401)

    def test_cors_only_allows_configured_origin(self):
        ok  = client.options("/review", headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"})
        bad = client.options("/review", headers={"Origin": "https://evil.com",      "Access-Control-Request-Method": "POST"})
        self.assertEqual(ok.headers.get("access-control-allow-origin"), "http://localhost:3000")
        self.assertIsNone(bad.headers.get("access-control-allow-origin"))


class QaUrlRegressionTests(unittest.TestCase):
    def test_l7_leading_zero_and_commit_links_canonicalise(self):
        self.assertEqual(canonical_pr_url("https://github.com/o/r/pull/01"), "https://github.com/o/r/pull/1")
        self.assertEqual(canonical_pr_url("https://github.com/o/r/pull/5/commits/abc1234def"), "https://github.com/o/r/pull/5")

    def test_l3_and_m11_github_errors_are_clean(self):
        import requests
        from unittest.mock import MagicMock
        from tools import github
        with patch.object(github.requests, "get", side_effect=requests.ConnectionError("NameResolutionError api.github.com")):
            with self.assertRaises(ValueError) as e:
                github.fetch_pr_diff("https://github.com/o/r/pull/1")
        self.assertNotIn("NameResolution", str(e.exception))
        limited = MagicMock(status_code=403, ok=False, headers={"X-RateLimit-Remaining": "0"})
        with patch.object(github.requests, "get", return_value=limited):
            with self.assertRaises(ValueError) as e:
                github.fetch_pr_diff("https://github.com/o/r/pull/1")
        self.assertIn("rate limit", str(e.exception))


if __name__ == "__main__":
    unittest.main()
