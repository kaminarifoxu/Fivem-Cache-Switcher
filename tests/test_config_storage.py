import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from ganov.core import open_user_store


class ConfigStorageTests(unittest.TestCase):
    def test_import_and_reopen_after_exe_moves(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            os.environ, {"LOCALAPPDATA": tmp}
        ):
            old = Path(tmp) / "old"
            old.mkdir()
            legacy = old / "remake_config.json"
            legacy.write_text(
                json.dumps(
                    {
                        "fivem_path": str(old),
                        "profiles": {"abc": "Kota A"},
                        "active_id": "abc",
                    }
                )
            )
            store = open_user_store(str(old))
            self.assertEqual(store.profiles, {"abc": "Kota A"})
            self.assertTrue(Path(store.config_path).is_file())
            legacy.unlink()
            reopened = open_user_store(str(Path(tmp) / "moved"))
            self.assertEqual(reopened.profiles, store.profiles)
            self.assertEqual(reopened.active_id, "abc")

    def test_corrupt_legacy_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            os.environ, {"LOCALAPPDATA": tmp}
        ):
            old = Path(tmp) / "old"
            old.mkdir()
            legacy = old / "remake_config.json"
            legacy.write_text("{broken")
            store = open_user_store(str(old))
            self.assertIsNotNone(store.load_warning)
            self.assertFalse(Path(store.config_path).exists())
            self.assertEqual(legacy.read_text(), "{broken")
