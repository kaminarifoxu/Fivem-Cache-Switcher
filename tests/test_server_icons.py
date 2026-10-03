import io
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
from ganov.server_icons import decode_icon, load_icon, MAX_BYTES


def png():
    buffer = io.BytesIO()
    Image.new("RGBA", (96, 96), "red").save(buffer, format="PNG")
    return buffer.getvalue()


class ServerIconTests(unittest.TestCase):
    def test_signed_version_download_is_cached_and_available_offline(self):
        with tempfile.TemporaryDirectory() as cache:
            with patch(
                "ganov.server_icons.urlopen", return_value=io.BytesIO(png())
            ) as request:
                self.assertEqual(load_icon("abc123", -796123261, cache).size, (64, 64))
                self.assertIn(
                    "/abc123/-796123261.png", request.call_args.args[0].full_url
                )
            with patch(
                "ganov.server_icons.urlopen", side_effect=OSError("offline")
            ) as request:
                self.assertIsNotNone(load_icon("abc123", -796123261, cache))
                request.assert_not_called()
                self.assertIsNotNone(load_icon("abc123", 42, cache))
                self.assertIsNotNone(load_icon("abc123", None, cache))

    def test_bad_images_do_not_replace_cached_logo(self):
        with tempfile.TemporaryDirectory() as cache:
            with patch("ganov.server_icons.urlopen", return_value=io.BytesIO(png())):
                load_icon("abc123", 1, cache)
            with patch(
                "ganov.server_icons.urlopen", return_value=io.BytesIO(b"not png")
            ):
                self.assertIsNotNone(load_icon("abc123", 2, cache))
        for raw in (b"not png", b"x" * (MAX_BYTES + 1)):
            with self.assertRaises((ValueError, OSError)):
                decode_icon(raw)
        with self.assertRaises(ValueError):
            load_icon("../foo", 1, ".")

    def test_missing_logo_uses_placeholder(self):
        with tempfile.TemporaryDirectory() as cache:
            with patch("ganov.server_icons.urlopen") as request:
                self.assertIsNone(load_icon("abc123", 0, cache))
                self.assertIsNone(load_icon("abc123", True, cache))
                request.assert_not_called()
