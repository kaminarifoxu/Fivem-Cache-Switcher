# Copyright (c) 2026 GANOMABI / amiinarii.
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from ganov.core import CacheStore
from ganov import storage


class SimulatedCrash(BaseException):
    pass


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        install = self.root / "FiveM.app"
        (install / "data").mkdir(parents=True)
        (self.root / "FiveM.exe").write_bytes(b"launcher")
        self.hdd = self.root / "HDD"
        self.hdd.mkdir()
        self.store = CacheStore(str(self.root / "config.json"), str(install))
        self.a = self.store.add("Jakarta")
        self.b = self.store.add("Bandung")
        for pid, content in [(self.a, b"A" * 2048), (self.b, b"B" * 3097)]:
            path = Path(self.store.backup(pid))
            (path / "empty" / "nested").mkdir(parents=True)
            (path / "marker").write_bytes(content)
        self.store.switch(self.a)
        # Exercise the cross-volume algorithm on every OS, even with one test disk.
        self.copy_patch = patch.object(storage, "same_volume", return_value=False)
        self.copy_patch.start()

    def tearDown(self):
        self.copy_patch.stop()
        self.temp.cleanup()

    def enable(self):
        self.store.configure_archive(str(self.hdd))

    def reopen(self):
        self.store = CacheStore(self.store.config_path)

    def check_bytes(self, active):
        self.assertEqual(self.store.detect(), active)
        for pid, content in [(self.a, b"A" * 2048), (self.b, b"B" * 3097)]:
            location = self.store.active if pid == active else self.store.backup(pid)
            self.assertEqual((Path(location) / "marker").read_bytes(), content)
            self.assertTrue((Path(location) / "empty" / "nested").is_dir())
        self.assertFalse(os.path.exists(self.store.journal))

    def test_enable_moves_only_inactive_cache_then_round_trip_and_disable(self):
        active_before = storage.inventory(self.store.active)
        self.enable()
        self.assertEqual(storage.inventory(self.store.active), active_before)
        self.assertTrue(os.path.isdir(self.store.cold_backup(self.b)))
        self.assertFalse(os.path.exists(self.store.local_backup(self.b)))
        self.reopen()
        self.store.switch(self.b)
        self.check_bytes(self.b)
        self.store.switch(self.a)
        self.check_bytes(self.a)
        self.store.configure_archive("")
        self.assertFalse(self.store.archive_root)
        self.assertTrue(os.path.isdir(self.store.local_backup(self.b)))
        self.check_bytes(self.a)

    def test_windows_different_drive_letters_are_allowed(self):
        with patch.object(
            storage.os.path, "commonpath", side_effect=ValueError("different drives")
        ):
            self.enable()
        self.check_bytes(self.a)

    def test_low_disk_space_retains_source_and_resumes_after_space_is_freed(self):
        usage = shutil.disk_usage(self.hdd)
        with patch.object(
            storage.shutil, "disk_usage", return_value=usage._replace(free=1)
        ):
            with self.assertRaisesRegex(RuntimeError, "Ruang tujuan"):
                self.enable()
        self.assertEqual(
            (Path(self.store.local_backup(self.b)) / "marker").read_bytes(), b"B" * 3097
        )
        self.assertTrue(os.path.isfile(self.store.journal))
        self.reopen()
        self.store.recover()
        self.check_bytes(self.a)

    def test_locked_copy_retains_source_and_recovery_restarts_partial_copy(self):
        original_open = open

        def locked(path, mode="r", *args, **kwargs):
            if str(path).endswith("marker") and mode == "xb":
                raise PermissionError("locked file")
            return original_open(path, mode, *args, **kwargs)

        with patch("builtins.open", side_effect=locked):
            with self.assertRaises(PermissionError):
                self.enable()
        self.assertTrue(os.path.exists(self.store.local_backup(self.b)))
        self.reopen()
        self.store.recover()
        self.check_bytes(self.a)

    def test_corrupt_copy_never_deletes_the_original(self):
        original = storage.inventory

        def corrupt(path, *args):
            result = original(path, *args)
            if ".ganov-partial-" in str(path):
                result["files"]["marker"] = (3097, "wrong hash")
            return result

        with patch.object(storage, "inventory", side_effect=corrupt):
            with self.assertRaisesRegex(RuntimeError, "Verifikasi"):
                self.enable()
        self.assertEqual(
            (Path(self.store.local_backup(self.b)) / "marker").read_bytes(), b"B" * 3097
        )
        self.store.recover()
        self.check_bytes(self.a)

    def test_crash_after_destination_promotion_and_partial_source_cleanup(self):
        self.enable()
        original = shutil.rmtree

        def crash(path, *args, **kwargs):
            if str(path) == self.store.active:
                (Path(path) / "marker").unlink()
                raise SimulatedCrash()
            return original(path, *args, **kwargs)

        with patch.object(storage.shutil, "rmtree", side_effect=crash):
            with self.assertRaises(SimulatedCrash):
                self.store.switch(self.b)
        self.reopen()
        self.store.recover()
        self.check_bytes(self.b)

    def test_crash_after_each_move_and_after_config_commit_resumes_forward(self):
        self.enable()
        original = storage.verified_move
        for fail_after in (1, 2):
            calls = 0

            def crash(*args):
                nonlocal calls
                original(*args)
                calls += 1
                if calls == fail_after:
                    raise SimulatedCrash()

            with patch.object(storage, "verified_move", side_effect=crash):
                with self.assertRaises(SimulatedCrash):
                    self.store.switch(self.b)
            self.reopen()
            self.store.recover()
            self.check_bytes(self.b)
            self.store.switch(self.a)
        original_save = self.store.save

        def committed_then_crash():
            original_save()
            raise SimulatedCrash()

        with patch.object(self.store, "save", side_effect=committed_then_crash):
            with self.assertRaises(SimulatedCrash):
                self.store.switch(self.b)
        self.reopen()
        self.store.recover()
        self.check_bytes(self.b)

    def test_missing_hdd_blocks_switch_without_recreating_it(self):
        self.enable()
        offline = self.root / "unplugged"
        self.hdd.rename(offline)
        self.assertFalse(self.store.storage_online())
        self.assertEqual(self.store.detect(), self.a)
        with self.assertRaisesRegex(RuntimeError, "tidak tersedia"):
            self.store.switch(self.b)
        self.assertFalse(self.hdd.exists())
        self.assertEqual((Path(self.store.active) / "marker").read_bytes(), b"A" * 2048)

    def test_collisions_and_journal_path_tampering_never_overwrite(self):
        self.enable()
        shutil.copytree(self.store.cold_backup(self.b), self.store.local_backup(self.b))
        with self.assertRaisesRegex(RuntimeError, "dua salinan"):
            self.store.switch(self.b)
        shutil.rmtree(self.store.local_backup(self.b))
        before = self.store.snapshot()
        record = {
            "kind": "tiered-storage",
            "before": before,
            "after": before,
            "moves": [[str(self.root), self.store.cold_backup(self.b)]],
            "index": 0,
            "token": "a" * 32,
        }
        Path(self.store.journal).write_text(json.dumps(record))
        with self.assertRaisesRegex(RuntimeError, "di luar"):
            self.store.recover()
        self.assertTrue(self.root.exists())

    def test_symlink_rejected_without_touching_external_file(self):
        external = self.root / "external"
        external.write_bytes(b"keep me")
        try:
            os.symlink(external, Path(self.store.backup(self.b)) / "link")
        except (OSError, NotImplementedError):
            self.skipTest("symlink privilege unavailable")
        with self.assertRaisesRegex(RuntimeError, "link"):
            self.enable()
        self.assertEqual(external.read_bytes(), b"keep me")
        self.assertTrue(os.path.isdir(self.store.local_backup(self.b)))

    def test_archive_add_delete_and_change_root_keep_owned_installation(self):
        self.enable()
        pid = self.store.add("New city")
        self.assertEqual(self.store.profile_location(pid), "archive")
        destination = self.store.delete(pid)
        self.assertTrue(Path(destination).is_relative_to(self.hdd))
        other = self.root / "Second HDD"
        other.mkdir()
        self.store.configure_archive(str(other))
        self.check_bytes(self.a)
        self.assertTrue(Path(self.store.backup(self.b)).is_relative_to(other))
        self.store.select_exe(self.store.exe)
        self.check_bytes(self.a)

    def test_source_mutation_after_copy_is_preserved(self):
        original = storage.inventory
        hits = 0

        def change_source(path, *args):
            nonlocal hits
            result = original(path, *args)
            if ".ganov-partial-" in str(path):
                (Path(self.store.local_backup(self.b)) / "new-file").write_bytes(b"new")
            return result

        with patch.object(storage, "inventory", side_effect=change_source):
            with self.assertRaisesRegex(RuntimeError, "Verifikasi"):
                self.enable()
        self.assertEqual(
            (Path(self.store.local_backup(self.b)) / "new-file").read_bytes(), b"new"
        )

    def test_live_fivem_blocks_any_storage_operation(self):
        with patch(
            "ganov.core.no_fivem", side_effect=RuntimeError("FiveM masih berjalan")
        ):
            with self.assertRaisesRegex(RuntimeError, "FiveM"):
                self.enable()
        self.assertFalse((self.hdd / "GanoV-Cache-Switch").exists())

    def test_same_volume_uses_atomic_rename_and_preserves_bytes(self):
        with patch.object(storage, "same_volume", return_value=True):
            self.enable()
            self.store.switch(self.b)
        self.check_bytes(self.b)

    def test_wrong_vault_marker_is_never_accepted(self):
        self.enable()
        marker = Path(self.store.vault()) / ".ganov-vault.json"
        marker.write_text(json.dumps({"data_dir": "different installation"}))
        with self.assertRaisesRegex(RuntimeError, "tidak cocok"):
            self.store.switch(self.b)
        self.assertEqual((Path(self.store.active) / "marker").read_bytes(), b"A" * 2048)

    def test_transfer_between_real_different_filesystems_when_available(self):
        candidate = "/dev/shm" if os.name != "nt" else "D:\\"
        if not os.path.isdir(candidate):
            self.skipTest("No second filesystem available")
        try:
            other = tempfile.TemporaryDirectory(prefix="ganov-test-", dir=candidate)
        except OSError:
            self.skipTest("Second filesystem is not writable")
        self.addCleanup(other.cleanup)
        if os.stat(other.name).st_dev == os.stat(self.store.data_dir).st_dev:
            self.skipTest("Test folders are on one filesystem")
        self.copy_patch.stop()
        self.store.configure_archive(other.name)
        self.store.switch(self.b)
        self.check_bytes(self.b)
        self.store.configure_archive("")
        self.check_bytes(self.b)
