# Copyright (c) 2026 GANOMABI / amiinarii.
import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
import cache_switcher as app


class UpdateTests(unittest.TestCase):
    def release(self, tag="v2.4.0", **overrides):
        data = {"tag_name": tag, "draft": False, "prerelease": False,
                "html_url": app.RELEASES_URL + "/tag/" + str(tag)}
        data.update(overrides)
        return data

    def check(self, data, current="2.3.0"):
        with patch("urllib.request.urlopen", return_value=io.BytesIO(json.dumps(data).encode())) as request:
            result = app.check_latest_release(current)
            self.assertEqual(request.call_args.kwargs["timeout"], 8)
            return result

    def test_newer_release_and_numeric_comparison(self):
        self.assertEqual(self.check(self.release("v2.10.0"), "2.9.0")["version"], "2.10.0")

    def test_equal_and_older_versions(self):
        self.assertIsNone(self.check(self.release("v2.3.0")))
        self.assertIsNone(self.check(self.release("v2.2.0")))

    def test_draft_and_prerelease_ignored(self):
        self.assertIsNone(self.check(self.release(draft=True)))
        self.assertIsNone(self.check(self.release(prerelease=True)))

    def test_no_published_release(self):
        with patch("urllib.request.urlopen", side_effect=HTTPError("url", 404, "Not Found", {}, None)):
            self.assertIsNone(app.check_latest_release())

    def test_failure_is_reported_to_ui_worker(self):
        with patch("urllib.request.urlopen", side_effect=URLError("offline")):
            with self.assertRaises(URLError):
                app.check_latest_release()

    def test_invalid_version_and_url(self):
        for tag in (None, "2.4", "v2.4.0-beta", "2.4.x"):
            with self.assertRaises(ValueError):
                self.check(self.release(tag))
        with self.assertRaises(ValueError):
            self.check(self.release(html_url="https://example.com/download"))

    def test_invalid_json(self):
        with patch("urllib.request.urlopen", return_value=io.BytesIO(b"not json")):
            with self.assertRaises(ValueError):
                app.check_latest_release()


if __name__ == "__main__":
    unittest.main()
