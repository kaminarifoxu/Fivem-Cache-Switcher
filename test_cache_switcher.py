# Copyright (c) 2026 GANOMABI / amiinarii.
import importlib.util
import json
import os
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("app", os.path.join(os.path.dirname(__file__), "cache_switcher.py"))
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = self.temp.name
        path = os.path.join(self.root, "FiveM.app")
        os.mkdir(path)
        os.mkdir(os.path.join(path, "data"))
        with open(os.path.join(self.root, "FiveM.exe"), "wb") as f:
            f.write(b"test launcher")
        self.store = app.CacheStore(os.path.join(self.root, "remake_config.json"), path)
        self.process_patch = patch.object(app, "no_fivem")
        self.process_patch.start()

    def tearDown(self):
        self.process_patch.stop()
        self.temp.cleanup()

    def put(self, folder, content):
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, "marker"), "w") as f:
            f.write(content)

    def read(self, folder):
        with open(os.path.join(folder, "marker")) as f:
            return f.read()

    def profiles(self):
        a, b = self.store.add("Jakarta"), self.store.add("Bandung")
        self.put(self.store.backup(a), "A")
        self.put(self.store.backup(b), "B")
        return a, b

    def test_round_trip_preserves_cache_bytes(self):
        a, b = self.profiles()
        self.store.switch(a)
        self.store.switch(b)
        self.assertEqual(self.read(self.store.active), "B")
        self.assertEqual(self.read(self.store.backup(a)), "A")
        self.store.switch(a)
        self.assertEqual(self.read(self.store.active), "A")
        self.assertEqual(self.read(self.store.backup(b)), "B")
        self.assertEqual(app.CacheStore(self.store.config_path).detect(), a)

    def test_existing_unidentified_cache_is_preserved(self):
        a, b = self.profiles()
        self.put(self.store.active, "OLD")
        self.store.switch(a)
        old = next(p for p in self.store.profiles if p not in [a, b])
        self.assertEqual(self.read(self.store.backup(old)), "OLD")

    def test_failed_second_rename_rolls_back(self):
        a, b = self.profiles()
        self.store.switch(a)
        real_rename = os.rename
        def fail_once(src, dst):
            if src == self.store.backup(b) and dst == self.store.active:
                raise PermissionError("locked")
            return real_rename(src, dst)
        with patch.object(os, "rename", side_effect=fail_once):
            with self.assertRaises(PermissionError):
                self.store.switch(b)
        self.assertEqual(self.store.detect(), a)
        self.assertEqual(self.read(self.store.active), "A")
        self.assertEqual(self.read(self.store.backup(b)), "B")
        self.assertFalse(os.path.exists(self.store.journal))

    def test_recovery_after_each_crash_stage(self):
        a, b = self.profiles()
        self.store.switch(a)
        for stage in [0, 1, 2, 3]:
            before = self.store.snapshot()
            app.atomic_json(self.store.journal, {"old": a, "target": b, "before": before})
            if stage >= 1:
                os.rename(self.store.active, self.store.backup(a))
            if stage >= 2:
                os.rename(self.store.backup(b), self.store.active)
            if stage >= 3:
                self.store.active_id = b
                self.store.save()
            reopened = app.CacheStore(self.store.config_path)
            reopened.recover()
            self.store = reopened
            self.assertEqual(self.read(self.store.active), "A")
            self.assertEqual(self.read(self.store.backup(b)), "B")
            self.assertEqual(self.store.detect(), a)

    def test_deletion_moves_to_recovery_folder(self):
        a, b = self.profiles()
        self.store.switch(a)
        destination = self.store.delete(a)
        self.assertEqual(self.read(destination), "A")
        self.assertNotIn(a, self.store.profiles)
        self.assertEqual(self.read(self.store.backup(b)), "B")

    def test_detection_never_deletes_or_guesses(self):
        a, b = self.profiles()
        self.put(self.store.active, "OLD")
        before = sorted(os.listdir(self.store.data_dir))
        self.assertEqual(self.store.detect(), "external")
        self.assertEqual(before, sorted(os.listdir(self.store.data_dir)))
        os.remove(os.path.join(self.store.backup(a), "marker"))
        os.rmdir(self.store.backup(a))
        os.remove(os.path.join(self.store.backup(b), "marker"))
        os.rmdir(self.store.backup(b))
        self.assertEqual(self.store.detect(), "conflict")
        with self.assertRaises(RuntimeError):
            self.store.switch(a)
        self.assertEqual(self.read(self.store.active), "OLD")

    def test_malicious_profile_id_rejected(self):
        with self.assertRaises(ValueError):
            self.store.backup("../../outside")

    def test_symlink_cache_rejected(self):
        a, b = self.profiles()
        os.remove(os.path.join(self.store.backup(b), "marker"))
        os.rmdir(self.store.backup(b))
        os.symlink(self.store.backup(a), self.store.backup(b))
        with self.assertRaises(RuntimeError):
            self.store.switch(b)
        self.assertEqual(self.read(self.store.backup(a)), "A")

    def test_original_config_import(self):
        a, b = self.profiles()
        self.store.switch(a)
        with open(os.path.join(self.root, "config.json"), "w") as f:
            json.dump({"fivem_path": self.store.path, "profiles": self.store.profiles}, f)
        os.remove(self.store.config_path)
        imported = app.CacheStore(self.store.config_path)
        self.assertEqual(imported.detect(), a)
        self.assertEqual(imported.profiles[b], "Bandung")

    def test_launcher_resolves_application_data_with_spaces(self):
        path = os.path.join(self.root, "FiveM Application Data", "data")
        self.put(os.path.join(path, "server-cache-priv"), "LIVE")
        exe = os.path.join(self.root, "FiveM.exe")
        self.assertEqual(app.find_data_directories(exe), [path])
        self.store.select_exe(exe)
        self.assertEqual(self.store.active, os.path.join(path, "server-cache-priv"))
        self.assertEqual(self.read(self.store.active), "LIVE")
        self.store.validate()

    def test_launcher_supports_direct_and_custom_application_folders(self):
        exe = os.path.join(self.root, "FiveM.exe")
        for name in ["", "My FiveM Files"]:
            data = os.path.join(self.root, name, "data")
            self.put(os.path.join(data, "server-cache-priv"), "LIVE")
            self.assertEqual(app.find_data_directories(exe), [os.path.normpath(data)])
            os.remove(os.path.join(data, "server-cache-priv", "marker"))
            os.rmdir(os.path.join(data, "server-cache-priv"))

    def test_launcher_does_not_guess_between_two_cache_roots(self):
        for name in ["FiveM.app", "FiveM Application Data"]:
            self.put(os.path.join(self.root, name, "data", "server-cache-priv"), name)
        exe = os.path.join(self.root, "FiveM.exe")
        self.assertEqual(len(app.find_data_directories(exe)), 2)
        before = self.store.snapshot()
        with self.assertRaises(RuntimeError):
            self.store.select_exe(exe)
        self.assertEqual(self.store.snapshot(), before)

    def test_existing_backup_profiles_are_imported_without_modifying_cache(self):
        path = os.path.join(self.root, "FiveM Application Data", "data")
        self.put(os.path.join(path, "server-cache-priv"), "LIVE")
        self.put(os.path.join(path, "server-cache-priv_Kota_A"), "A")
        self.put(os.path.join(path, "server-cache-priv_Kota_B"), "B")
        before = sorted(os.listdir(path))
        self.store.select_exe(os.path.join(self.root, "FiveM.exe"))
        self.assertEqual(set(self.store.profiles), {"Kota_A", "Kota_B"})
        self.assertEqual(sorted(os.listdir(path)), before)
        self.assertEqual(self.store.detect(), "external")
        self.store.switch("Kota_B")
        self.assertEqual(self.read(self.store.active), "B")
        old = next(p for p, n in self.store.profiles.items() if n == "Cache sebelumnya")
        self.assertEqual(self.read(self.store.backup(old)), "LIVE")

    def test_reselecting_launcher_retains_names_and_active_profile(self):
        a, b = self.profiles()
        self.store.switch(a)
        self.store.select_exe(os.path.join(self.root, "FiveM.exe"))
        self.assertEqual(self.store.profiles[a], "Jakarta")
        self.assertEqual(self.store.detect(), a)
        reopened = app.CacheStore(self.store.config_path)
        self.assertEqual(reopened.exe, os.path.join(self.root, "FiveM.exe"))
        self.assertEqual(reopened.active, self.store.active)

    def test_bad_launcher_is_rejected(self):
        wrong = os.path.join(self.root, "NotFiveM.exe")
        with open(wrong, "wb") as f:
            f.write(b"test")
        with self.assertRaises(RuntimeError):
            app.find_data_directories(wrong)
        self.assertEqual(app.find_data_directories(os.path.join(self.root, "FiveM.exe")), [self.store.data_dir])

    def test_process_guard_blocks_mutation(self):
        a, b = self.profiles()
        with patch.object(app, "no_fivem", side_effect=RuntimeError("FiveM running")):
            with self.assertRaises(RuntimeError):
                self.store.switch(a)
        self.assertTrue(os.path.isdir(self.store.backup(a)))
        self.assertFalse(os.path.exists(self.store.active))

    def test_process_detection_ignores_own_exe_and_blocks_game(self):
        self.process_patch.stop()
        class Result:
            stdout = '"FiveM-Cache-Switcher-Remake.exe","123","Console"\n'
        with patch.object(app.os, "name", "nt"), patch.object(app.subprocess, "run", return_value=Result()):
            app.no_fivem()
            Result.stdout += '"FiveM_b3258_GTAProcess.exe","456","Console"\n'
            with self.assertRaises(RuntimeError):
                app.no_fivem()

    def test_cleaner_does_not_follow_links(self):
        temp = os.path.join(self.root, "Temp")
        outside = os.path.join(self.root, "outside")
        self.put(temp, "junk")
        self.put(outside, "KEEP")
        os.symlink(outside, os.path.join(temp, "linked"))
        removed, skipped = app.clean_temp([temp])
        self.assertEqual(self.read(outside), "KEEP")
        self.assertEqual((removed, skipped), (1, 1))


if __name__ == "__main__":
    unittest.main()
