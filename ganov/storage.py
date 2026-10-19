# Copyright (c) 2026 GANOMABI / amiinarii.
"""Owned cache vaults and resumable, verified transfers between storage volumes."""

import hashlib
import json
import os
import shutil
import stat
import time
import uuid
from pathlib import Path


def _core():
    from . import core

    return core


def normal(path):
    return os.path.normcase(os.path.abspath(path))


def plain_parents(path):
    for item in (Path(path), *Path(path).parents):
        if _core().is_link(str(item)):
            raise RuntimeError("Lokasi cache tidak boleh melewati symlink/junction.")


def inventory(path, progress=None):
    """Hash ordinary files, rejecting links and mutations instead of following them."""
    plain_parents(path)
    _core().check_tree(path)
    files, directories, done = {}, [], 0
    for base, dirs, names in os.walk(path, followlinks=False):
        for name in sorted(dirs):
            full = os.path.join(base, name)
            if _core().is_link(full):
                raise RuntimeError(
                    "Cache berisi symlink/junction; transfer dibatalkan."
                )
            directories.append(os.path.relpath(full, path))
        for name in sorted(names):
            full = os.path.join(base, name)
            before = os.stat(full, follow_symlinks=False)
            if _core().is_link(full) or not stat.S_ISREG(before.st_mode):
                raise RuntimeError(
                    "Cache berisi file khusus/link; transfer dibatalkan."
                )
            digest = hashlib.sha256()
            with open(full, "rb") as stream:
                while chunk := stream.read(4 * 1024 * 1024):
                    digest.update(chunk)
                    done += len(chunk)
                    if progress:
                        progress(done)
            after = os.stat(full, follow_symlinks=False)
            if (before.st_size, before.st_mtime_ns) != (
                after.st_size,
                after.st_mtime_ns,
            ):
                raise RuntimeError(
                    "Isi cache berubah selama transfer. Tutup FiveM dahulu."
                )
            files[os.path.relpath(full, path)] = (after.st_size, digest.hexdigest())
    return {"files": files, "dirs": sorted(directories)}


def fingerprint(manifest):
    encoded = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def same_volume(source, destination_parent):
    return os.stat(source).st_dev == os.stat(destination_parent).st_dev


def verified_move(source, destination, record, index, persist, progress):
    """Commit destination before source cleanup; record owns its temporary directory."""
    core = _core()
    core.no_fivem()
    plain_parents(source)
    plain_parents(destination)
    source_exists, dest_exists = os.path.lexists(source), os.path.lexists(destination)
    proof = record.get("verified", {})
    if dest_exists:
        core.check_tree(destination)
        if source_exists:
            if proof.get("index") != index:
                raise RuntimeError(
                    "Dua salinan cache ditemukan tanpa bukti transfer; tidak ditimpa."
                )
            target_data = inventory(destination)
            if fingerprint(target_data) != proof.get("digest"):
                raise RuntimeError(
                    "Salinan tujuan berubah. Salinan asal tetap dipertahankan."
                )
            remaining = inventory(source)
            if any(
                target_data["files"].get(k) != v for k, v in remaining["files"].items()
            ) or not set(remaining["dirs"]).issubset(target_data["dirs"]):
                raise RuntimeError(
                    "Salinan asal berubah. Periksa kedua cache sebelum melanjutkan."
                )
            core.no_fivem()
            progress("cleanup", 0, 0)
            shutil.rmtree(source)
        return
    if not source_exists:
        raise RuntimeError(
            "Cache sumber dan tujuan tidak ditemukan. Tidak ada data yang dihapus."
        )
    core.check_tree(source)
    core.check_tree(os.path.dirname(destination))
    stage = destination + ".ganov-partial-" + record["token"]
    if same_volume(source, os.path.dirname(destination)) and not os.path.lexists(stage):
        for base, dirs, names in os.walk(source, followlinks=False):
            if any(core.is_link(os.path.join(base, name)) for name in dirs + names):
                raise RuntimeError(
                    "Cache berisi symlink/junction; transfer dibatalkan."
                )
        core.no_fivem()
        os.rename(source, destination)
        return
    source_data = inventory(source, lambda n: progress("scan", n, 0))
    total = sum(size for size, _ in source_data["files"].values())
    if os.path.lexists(stage):
        if record.get("copying") != index:
            raise RuntimeError(
                "Folder sementara sudah ada dan tidak dimiliki transaksi ini."
            )
        plain_parents(stage)
        core.check_tree(stage)
        # Remove only this transaction's unfinished copy, never a source cache.
        inventory(stage)
        shutil.rmtree(stage)
    if shutil.disk_usage(os.path.dirname(destination)).free < total:
        raise RuntimeError(
            "Ruang tujuan tidak cukup. Kosongkan ruang, lalu klik Lanjutkan transfer."
        )
    record["copying"] = index
    record.pop("verified", None)
    persist()
    os.mkdir(stage)
    for directory in source_data["dirs"]:
        os.makedirs(os.path.join(stage, directory), exist_ok=True)
    done = 0
    # tasklist is expensive on Windows: poll by elapsed time, not file count.
    core.no_fivem()
    next_process_check = time.monotonic() + 1.0

    def check_running():
        nonlocal next_process_check
        now = time.monotonic()
        if now >= next_process_check:
            core.no_fivem()
            next_process_check = time.monotonic() + 1.0

    progress("copy", 0, total)
    for relative in source_data["files"]:
        check_running()
        with open(os.path.join(source, relative), "rb") as src, open(
            os.path.join(stage, relative), "xb"
        ) as dst:
            while chunk := src.read(4 * 1024 * 1024):
                check_running()
                dst.write(chunk)
                done += len(chunk)
                progress("copy", done, total)
            dst.flush()
            os.fsync(dst.fileno())
    progress("verify", 0, total)
    staged_data = inventory(stage, lambda n: progress("verify", n, total))
    if staged_data != source_data or inventory(source) != source_data:
        raise RuntimeError(
            "Verifikasi cache gagal; salinan asal belum dihapus. Lanjutkan transfer untuk mencoba lagi."
        )
    core.no_fivem()
    record["verified"] = {"index": index, "digest": fingerprint(staged_data)}
    persist()
    os.rename(stage, destination)
    progress("cleanup", 0, total)
    core.no_fivem()
    # A crash here leaves the full destination plus a recoverable source remainder.
    shutil.rmtree(source)


class StorageMixin:
    @property
    def archive_root(self):
        return self.archive_roots.get(normal(self.data_dir), "")

    def local_backup(self, pid):
        if not _core().safe_id(pid):
            raise ValueError("ID profil tidak valid")
        return os.path.join(self.data_dir, _core().PREFIX + pid)

    def vault_path(self, root=None):
        root = self.archive_root if root is None else root
        key = hashlib.sha256(normal(self.data_dir).encode()).hexdigest()[:16]
        return os.path.join(root, "GanoV-Cache-Switch", key)

    def vault(self, root=None, create=False):
        root = self.archive_root if root is None else root
        if not root or not os.path.isdir(root):
            raise RuntimeError(
                "Lokasi arsip HDD tidak tersedia. Sambungkan drive yang benar."
            )
        plain_parents(root)
        path = self.vault_path(root)
        # A vault cannot sit inside FiveM's live data directory, or contain it.
        try:
            nested = os.path.commonpath([normal(path), normal(self.data_dir)]) in (
                normal(path),
                normal(self.data_dir),
            )
        except (
            ValueError
        ):  # Windows paths on different drive letters have no common root.
            nested = False
        if nested:
            raise RuntimeError("Pilih lokasi arsip di luar folder data FiveM.")
        plain_parents(path)
        marker = os.path.join(path, ".ganov-vault.json")
        if create and not os.path.lexists(path):
            os.makedirs(path)
            _core().atomic_json(marker, {"data_dir": normal(self.data_dir)})
        try:
            if _core().is_link(marker):
                raise ValueError("linked marker")
            with open(marker, encoding="utf-8") as stream:
                data = json.load(stream)
            if data != {"data_dir": normal(self.data_dir)}:
                raise ValueError("wrong installation")
        except (OSError, ValueError, TypeError) as error:
            raise RuntimeError(
                "Arsip HDD tidak cocok dengan instalasi ini; tidak ada folder yang ditimpa."
            ) from error
        return path

    def cold_backup(self, pid, root=None):
        if not _core().safe_id(pid):
            raise ValueError("ID profil tidak valid")
        return os.path.join(self.vault_path(root), _core().PREFIX + pid)

    def storage_online(self):
        if not self.archive_root:
            return True
        try:
            self.vault()
            return True
        except (OSError, ValueError, RuntimeError):
            return False

    def profile_location(self, pid):
        if pid == self.detect():
            return "active"
        if os.path.lexists(self.local_backup(pid)):
            return "local"
        return "archive" if self.archive_root else "missing"

    def ensure_storage_idle(self):
        _core().no_fivem()
        self.validate()
        if os.path.isfile(self.journal):
            raise RuntimeError(
                "Transfer sebelumnya belum selesai. Klik Lanjutkan transfer."
            )

    def configure_archive(self, folder, progress=None):
        self.ensure_storage_idle()
        if folder:
            folder = os.path.abspath(folder)
            self.vault(folder, create=True)
        elif self.archive_root:
            self.vault()
        before = self.snapshot()
        after = self.snapshot()
        if folder:
            after["archive_roots"][normal(self.data_dir)] = folder
        else:
            after["archive_roots"].pop(normal(self.data_dir), None)
        roots = [self.data_dir]
        if self.archive_root:
            roots.append(self.vault())
        if folder:
            roots.append(self.vault(folder))
        roots = list(dict.fromkeys(roots))
        active = self.detect()
        if active == "conflict":
            raise RuntimeError(
                "Periksa backup yang hilang sebelum mengubah penyimpanan."
            )
        moves = []
        for pid in self.profiles:
            sources = [
                os.path.join(root, _core().PREFIX + pid)
                for root in roots
                if os.path.lexists(os.path.join(root, _core().PREFIX + pid))
            ]
            if len(sources) > 1:
                raise RuntimeError(
                    "Profil memiliki dua salinan; tidak ada cache yang ditimpa."
                )
            if pid == active:
                continue
            if not sources:
                raise RuntimeError(
                    "Backup profil tidak ditemukan: " + self.profiles[pid]
                )
            destination = (
                self.cold_backup(pid, folder) if folder else self.local_backup(pid)
            )
            if normal(sources[0]) != normal(destination):
                moves.append([sources[0], destination])
        self._start_storage(before, after, moves, progress)

    def tiered_switch(self, target, progress=None):
        self.ensure_storage_idle()
        self.vault()
        if target not in self.profiles:
            raise RuntimeError("Profil tidak ditemukan")
        current = self.detect()
        if current == "conflict":
            raise RuntimeError("Periksa backup yang hilang sebelum mengganti cache.")
        if target == current:
            return
        before, after = self.snapshot(), self.snapshot()
        moves = []
        # Flush any legacy SSD backups before parking the active city.
        for pid in self.profiles:
            local, cold = self.local_backup(pid), self.cold_backup(pid)
            if os.path.lexists(local) and os.path.lexists(cold):
                raise RuntimeError(
                    "Profil memiliki dua salinan; tidak ada cache yang ditimpa."
                )
            if pid not in (target, current) and os.path.isdir(local):
                moves.append([local, cold])
        if os.path.lexists(self.active):
            _core().check_tree(self.active)
            if current == "external":
                current = self.next_id()
                after["profiles"][current] = "Cache sebelumnya"
            if (
                not current
                or os.path.lexists(self.cold_backup(current))
                or os.path.lexists(self.local_backup(current))
            ):
                raise RuntimeError("Backup cache aktif sudah ada; periksa salinannya.")
            moves.append([self.active, self.cold_backup(current)])
        _core().check_tree(self.backup(target))
        moves.append([self.backup(target), self.active])
        after["active_id"] = target
        self._start_storage(before, after, moves, progress)

    def _start_storage(self, before, after, moves, progress):
        record = {
            "kind": "tiered-storage",
            "before": before,
            "after": after,
            "moves": moves,
            "index": 0,
            "token": uuid.uuid4().hex,
        }
        _core().atomic_json(self.journal, record)
        self._resume_storage(record, progress)

    def _resume_storage(self, record, progress=None):
        """Resume forward: verified destinations become authoritative; never overwrite."""
        core = _core()
        core.no_fivem()
        before, after = record.get("before", {}), record.get("after", {})
        for snapshot in (before, after):
            if not isinstance(snapshot, dict) or normal(
                snapshot.get("fivem_path", "")
            ) != normal(self.path):
                raise RuntimeError("Catatan transfer tidak cocok dengan instalasi ini.")
            profiles = snapshot.get("profiles")
            if not isinstance(profiles, dict) or any(
                not core.safe_id(k) or not isinstance(v, str)
                for k, v in profiles.items()
            ):
                raise RuntimeError("Catatan profil transfer tidak valid.")
            if (
                snapshot.get("active_id") is not None
                and snapshot["active_id"] not in profiles
            ):
                raise RuntimeError("Profil aktif transfer tidak valid.")
        roots = {self.data_dir}
        for snapshot in (before, after):
            mapping = snapshot.get("archive_roots", {})
            if not isinstance(mapping, dict):
                raise RuntimeError("Catatan penyimpanan tidak valid.")
            root = mapping.get(normal(self.data_dir), "")
            if root:
                roots.add(self.vault(root))
        allowed = {normal(self.active)}
        for pid in set(before["profiles"]) | set(after["profiles"]):
            allowed.update(
                normal(os.path.join(root, core.PREFIX + pid)) for root in roots
            )
        token, moves, index = (
            record.get("token"),
            record.get("moves"),
            record.get("index"),
        )
        if (
            not isinstance(token, str)
            or len(token) != 32
            or any(c not in "0123456789abcdef" for c in token)
            or not isinstance(moves, list)
            or type(index) is not int
            or not 0 <= index <= len(moves)
        ):
            raise RuntimeError("Catatan transfer tidak valid.")
        for move in moves:
            if (
                not isinstance(move, list)
                or len(move) != 2
                or any(not isinstance(p, str) or normal(p) not in allowed for p in move)
                or normal(move[0]) == normal(move[1])
            ):
                raise RuntimeError("Path transfer di luar folder cache yang diizinkan.")
        persist = lambda: core.atomic_json(self.journal, record)
        for i in range(index, len(moves)):
            core.no_fivem()

            def notify(phase, done, total):
                if progress:
                    progress(phase, done, total, i, len(moves))

            verified_move(*moves[i], record, i, persist, notify)
            record["index"] = i + 1
            record.pop("copying", None)
            record.pop("verified", None)
            persist()
        self.profiles = dict(after["profiles"])
        self.active_id = after.get("active_id")
        self.archive_roots = dict(after.get("archive_roots", {}))
        self.save()
        os.remove(self.journal)
