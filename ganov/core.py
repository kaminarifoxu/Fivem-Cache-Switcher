# Copyright (c) 2026 GANOMABI / amiinarii.
"""GanoV-Cache-Switch. Copyright (c) 2026 GANOMABI / amiinarii."""

import os
import sys
import json
import shutil
import subprocess
import time
import threading
import ctypes

VERSION = "2.7.11"
APP_NAME = "GanoV-Cache-Switch"
COPYRIGHT = "Copyright (c) 2026 GANOMABI / amiinarii"
PREFIX = "server-cache-priv_"
GITHUB_REPOSITORY = "kaminarifoxu/Fivem-Cache-Switcher"
RELEASES_URL = "https://github.com/" + GITHUB_REPOSITORY + "/releases"


def user_config_path():
    root = os.environ.get("LOCALAPPDATA") or os.path.join(
        os.path.expanduser("~"), ".local", "share"
    )
    directory = os.path.join(root, APP_NAME)
    os.makedirs(directory, exist_ok=True)
    return os.path.join(directory, "remake_config.json")


def open_user_store(legacy_directory):
    target = user_config_path()
    if os.path.isfile(target):
        return CacheStore(target)
    for name in ("remake_config.json", "config.json"):
        legacy = os.path.join(legacy_directory, name)
        if os.path.isfile(legacy):
            store = CacheStore(legacy)
            store.config_path = target
            if not store.load_warning:
                store.save()
            return store
    return CacheStore(target)


def stable_version(tag):
    """Accept stable major.minor.patch tags, comparing numbers rather than text."""
    if not isinstance(tag, str):
        raise ValueError("Nomor versi tidak valid")
    parts = tag.removeprefix("v").split(".")
    if len(parts) != 3 or any(
        not p or not p.isascii() or not p.isdecimal() for p in parts
    ):
        raise ValueError("Gunakan versi stabil seperti v2.3.0")
    return tuple(int(p) for p in parts)


def summarize_release_notes(body):
    """Keep a short, plain-text list from the GitHub release body."""
    import re

    if not isinstance(body, str):
        return ""
    lines = []
    for line in body[:16000].splitlines():
        line = line.strip()
        if not re.match(r"^[-*+]\s+|^\d+[.)]\s+", line):
            continue
        line = re.sub(r"^[-*+]\s+|^\d+[.)]\s+", "", line)
        line = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", line)
        line = line.replace("**", "").replace("`", "").strip()
        line = "".join(c for c in line if c.isprintable())
        if line:
            lines.append("• " + (line[:137] + "…" if len(line) > 140 else line))
        if len(lines) == 4:
            break
    return "\n".join(lines)


def check_latest_release(current=VERSION):
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError

    request = Request(
        "https://api.github.com/repos/" + GITHUB_REPOSITORY + "/releases/latest",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": APP_NAME + "/" + current,
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urlopen(request, timeout=8) as response:
            raw = response.read(1024 * 1024 + 1)
    except HTTPError as e:
        if e.code == 404:
            return None
        raise
    if len(raw) > 1024 * 1024:
        raise ValueError("Respons update terlalu besar")
    release = json.loads(raw)
    if not isinstance(release, dict):
        raise ValueError("Respons update tidak valid")
    if release.get("draft") or release.get("prerelease"):
        return None
    tag = release.get("tag_name")
    if stable_version(tag) <= stable_version(current):
        return None
    url = release.get("html_url", "")
    if not isinstance(url, str) or not url.startswith(RELEASES_URL + "/tag/"):
        raise ValueError("Alamat rilis tidak valid")
    from .auto_updater import release_asset

    return {
        "version": tag.removeprefix("v"),
        "url": url,
        "summary": summarize_release_notes(release.get("body")),
        **release_asset(release, GITHUB_REPOSITORY),
    }


def open_release_page(url):
    if not url.startswith(RELEASES_URL + "/tag/"):
        raise ValueError("Alamat rilis tidak valid")
    if os.name == "nt":
        os.startfile(url)
    else:
        import webbrowser

        webbrowser.open(url)


def nearby_exe(path):
    for candidate in [
        os.path.join(path, "FiveM.exe"),
        os.path.join(os.path.dirname(path), "FiveM.exe"),
    ]:
        if os.path.isfile(candidate):
            return os.path.abspath(candidate)
    return ""


def find_data_directories(exe):
    """Resolve launcher -> application data without depending on a folder name."""
    if not os.path.isfile(exe) or os.path.basename(exe).lower() != "fivem.exe":
        raise RuntimeError("Pilih file FiveM.exe yang valid.")
    root = os.path.dirname(os.path.abspath(exe))
    bases = [root]
    try:
        bases += [
            os.path.join(root, n)
            for n in os.listdir(root)
            if os.path.isdir(os.path.join(root, n))
            and not is_link(os.path.join(root, n))
        ]
    except OSError:
        pass
    strong, normal = [], []
    for base in bases:
        data = os.path.join(base, "data")
        if not os.path.isdir(data) or is_link(data):
            continue
        try:
            names = os.listdir(data)
        except OSError:
            continue
        if any(n == "server-cache-priv" or n.startswith(PREFIX) for n in names):
            strong.append(os.path.abspath(data))
        elif (
            os.path.basename(base).lower() in ["fivem.app", "fivem application data"]
            or os.path.isdir(os.path.join(base, "citizen"))
            or any(n in names for n in ["server-cache", "game-storage", "nui-storage"])
        ):
            normal.append(os.path.abspath(data))
    return list(dict.fromkeys(strong or normal))


def safe_id(value):
    return (
        isinstance(value, str)
        and value
        and all(
            c in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
            for c in value
        )
    )


def atomic_json(path, data):
    tmp = path + ".new"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def is_link(path):
    return os.path.islink(path) or (
        hasattr(os.path, "isjunction") and os.path.isjunction(path)
    )


def check_tree(path):
    if is_link(path):
        raise RuntimeError("Folder adalah symlink/junction. Pilih folder cache biasa.")
    if not os.path.isdir(path):
        raise RuntimeError("Folder cache tidak ditemukan: " + path)


def no_fivem():
    if os.name != "nt":
        return
    result = subprocess.run(
        ["tasklist", "/FO", "CSV", "/NH"],
        capture_output=True,
        text=True,
        creationflags=0x08000000,
        timeout=15,
        check=True,
    )
    for line in result.stdout.splitlines():
        name = line.split('",')[0].strip('"').lower()
        if name == "fivem.exe" or (name.startswith("fivem_") and name.endswith(".exe")):
            raise RuntimeError(
                "FiveM masih berjalan. Tutup FiveM sepenuhnya sebelum mengubah cache."
            )


class CacheStore:
    def __init__(self, config_path, default_path=None):
        self.config_path = config_path
        self.path = default_path or os.path.join(
            os.environ.get("LOCALAPPDATA", ""), "FiveM", "FiveM.app"
        )
        self.exe = nearby_exe(self.path)
        self.profiles = {}
        self.active_id = None
        self.load_warning = None
        source = config_path
        if not os.path.isfile(source):
            legacy = os.path.join(os.path.dirname(source), "config.json")
            if os.path.isfile(legacy):
                source = legacy
        if os.path.isfile(source):
            try:
                with open(source, encoding="utf-8-sig") as f:
                    data = json.load(f)
                profiles = data.get("profiles", {})
                if not isinstance(profiles, dict) or any(
                    not safe_id(k) or not isinstance(v, str)
                    for k, v in profiles.items()
                ):
                    raise ValueError("Format profil tidak valid")
                path = data.get("fivem_path", self.path)
                if not isinstance(path, str) or not path.strip():
                    raise ValueError("Path FiveM tidak valid")
                self.path = os.path.abspath(path)
                exe = data.get("fivem_exe", "")
                if not isinstance(exe, str):
                    raise ValueError("Path FiveM.exe tidak valid")
                self.exe = os.path.abspath(exe) if exe else nearby_exe(self.path)
                self.profiles = profiles
                self.active_id = (
                    data.get("active_id") if data.get("active_id") in profiles else None
                )
            except Exception as e:
                self.load_warning = (
                    "Konfigurasi gagal dibaca; file asli tetap tersedia.\n" + str(e)
                )
        if not self.exe:
            launcher = os.path.join(
                os.environ.get("LOCALAPPDATA", ""), "FiveM", "FiveM.exe"
            )
            if os.path.isfile(launcher):
                self.exe = os.path.abspath(launcher)
                locations = find_data_directories(self.exe)
                if len(locations) == 1 and not self.profiles:
                    self.path = os.path.dirname(locations[0])

    def select_exe(self, exe, data_dir=None):
        no_fivem()
        if os.path.isfile(self.journal):
            raise RuntimeError(
                "Pulihkan switch sebelumnya sebelum mengganti instalasi."
            )
        locations = find_data_directories(exe)
        if data_dir is None:
            if len(locations) != 1:
                raise RuntimeError(
                    "Folder data belum dapat ditentukan. Pilih folder data milik instalasi ini."
                )
            data_dir = locations[0]
        data_dir = os.path.abspath(data_dir)
        if (
            os.path.basename(data_dir).lower() != "data"
            or not os.path.isdir(data_dir)
            or is_link(data_dir)
        ):
            raise RuntimeError("Pilih folder data yang valid.")
        before = self.snapshot()
        self.exe = os.path.abspath(exe)
        new_path = os.path.dirname(data_dir)
        changed = os.path.normcase(new_path) != os.path.normcase(
            os.path.abspath(self.path)
        )
        self.path = new_path
        if changed:
            self.profiles, self.active_id = {}, None
        try:
            self.import_backups()
            self.save()
        except Exception:
            self.path, self.exe = before["fivem_path"], before["fivem_exe"]
            self.profiles, self.active_id = before["profiles"], before["active_id"]
            raise

    def import_backups(self):
        """List existing backups without renaming, deleting, or guessing the active city."""
        if not os.path.isdir(self.data_dir):
            return
        for name in sorted(os.listdir(self.data_dir)):
            if not name.startswith(PREFIX) or name.startswith(PREFIX + "temp_"):
                continue
            pid = name[len(PREFIX) :]
            path = os.path.join(self.data_dir, name)
            if (
                safe_id(pid)
                and pid not in self.profiles
                and os.path.isdir(path)
                and not is_link(path)
            ):
                self.profiles[pid] = pid.replace("_", " ")

    @property
    def data_dir(self):
        return os.path.join(self.path, "data")

    @property
    def active(self):
        return os.path.join(self.data_dir, "server-cache-priv")

    @property
    def journal(self):
        return os.path.join(self.data_dir, "cache-switcher-remake-journal.json")

    def backup(self, pid):
        if not safe_id(pid):
            raise ValueError("ID profil tidak valid")
        return os.path.join(self.data_dir, PREFIX + pid)

    def validate(self):
        if (
            not self.exe
            or not os.path.isfile(self.exe)
            or os.path.basename(self.exe).lower() != "fivem.exe"
        ):
            raise RuntimeError("Pilih FiveM.exe terlebih dahulu.")
        if not os.path.isdir(self.data_dir):
            raise RuntimeError(
                "Folder data instalasi ini tidak ditemukan. Pilih ulang FiveM.exe."
            )
        if self.load_warning:
            raise RuntimeError(
                self.load_warning + "\nPerbaiki konfigurasi sebelum mengubah cache."
            )
        if is_link(self.data_dir):
            raise RuntimeError("Folder data berupa symlink/junction.")

    def snapshot(self):
        return {
            "fivem_exe": self.exe,
            "fivem_path": self.path,
            "profiles": dict(self.profiles),
            "active_id": self.active_id,
        }

    def save(self):
        atomic_json(self.config_path, self.snapshot())

    def detect(self):
        if not os.path.isdir(self.active):
            return None
        missing = [p for p in self.profiles if not os.path.lexists(self.backup(p))]
        if self.active_id in missing and len(missing) == 1:
            return self.active_id
        if len(missing) == 1:
            return missing[0]
        if len(missing) > 1:
            return "conflict"
        return "external"

    def next_id(self):
        for n in range(1, 100000):
            pid = "Kota_" + str(n)
            if pid not in self.profiles and not os.path.lexists(self.backup(pid)):
                return pid
        raise RuntimeError("Tidak dapat membuat ID baru")

    def add(self, name):
        no_fivem()
        self.validate()
        if os.path.isfile(self.journal):
            raise RuntimeError("Pulihkan switch sebelumnya terlebih dahulu.")
        pid = self.next_id()
        os.mkdir(self.backup(pid))
        self.profiles[pid] = name
        try:
            self.save()
        except Exception:
            del self.profiles[pid]
            os.rmdir(self.backup(pid))
            raise
        return pid

    def rename(self, pid, name):
        old = self.profiles[pid]
        self.profiles[pid] = name
        try:
            self.save()
        except Exception:
            self.profiles[pid] = old
            raise

    def switch(self, target):
        no_fivem()
        self.validate()
        if target not in self.profiles:
            raise RuntimeError("Profil tidak ditemukan")
        if os.path.isfile(self.journal):
            raise RuntimeError("Switch sebelumnya belum selesai. Klik Pulihkan Switch.")
        current = self.detect()
        if current == target:
            return
        if current == "conflict":
            raise RuntimeError(
                "Beberapa backup tidak ditemukan. Periksa folder data; cache tidak akan ditebak."
            )
        check_tree(self.backup(target))
        before = self.snapshot()
        if os.path.lexists(self.active):
            check_tree(self.active)
        # Keep unidentified existing cache as its own profile rather than deleting it.
        if current == "external":
            current = self.next_id()
            self.profiles[current] = "Cache sebelumnya"
        if os.path.lexists(self.active):
            if os.path.lexists(self.backup(current)):
                self.profiles = before["profiles"]
                raise RuntimeError(
                    "Backup tujuan sudah ada. Switch dibatalkan untuk menjaga data."
                )
        old = current if os.path.isdir(self.active) else None
        record = {"old": old, "target": target, "before": before}
        try:
            atomic_json(self.journal, record)
        except Exception:
            self.profiles = before["profiles"]
            raise
        try:
            if old:
                os.rename(self.active, self.backup(old))
            os.rename(self.backup(target), self.active)
            self.active_id = target
            self.save()
            os.remove(self.journal)
        except Exception:
            try:
                self.recover()
            except Exception as recovery_error:
                raise RuntimeError(
                    "Switch terhenti; data tetap disimpan. Klik Pulihkan Switch.\n"
                    + str(recovery_error)
                )
            raise

    def recover(self):
        no_fivem()
        self.validate()
        with open(self.journal, encoding="utf-8") as f:
            record = json.load(f)
        old, target, before = (
            record.get("old"),
            record.get("target"),
            record.get("before"),
        )
        if (
            not safe_id(target)
            or (old is not None and not safe_id(old))
            or old == target
        ):
            raise RuntimeError("Catatan pemulihan tidak valid")
        if not isinstance(before, dict) or os.path.normcase(
            before.get("fivem_path", "")
        ) != os.path.normcase(self.path):
            raise RuntimeError("Path catatan pemulihan tidak cocok")
        profiles = before.get("profiles")
        if (
            not isinstance(profiles, dict)
            or target not in profiles
            or any(
                not safe_id(k) or not isinstance(v, str) for k, v in profiles.items()
            )
        ):
            raise RuntimeError("Profil pemulihan tidak valid")
        # Locations determine which atomic rename completed, even after a crash.
        if os.path.isdir(self.active) and not os.path.lexists(self.backup(target)):
            check_tree(self.active)
            os.rename(self.active, self.backup(target))
        if old and os.path.isdir(self.backup(old)) and not os.path.lexists(self.active):
            check_tree(self.backup(old))
            os.rename(self.backup(old), self.active)
        if old and not os.path.isdir(self.active):
            raise RuntimeError(
                "Cache sebelumnya tidak ditemukan. Periksa folder data secara manual."
            )
        if not os.path.isdir(self.backup(target)):
            raise RuntimeError(
                "Backup target tidak ditemukan. Periksa folder data secara manual."
            )
        self.profiles = profiles
        self.active_id = before.get("active_id")
        self.save()
        os.remove(self.journal)

    def delete(self, pid):
        no_fivem()
        self.validate()
        if os.path.isfile(self.journal):
            raise RuntimeError("Pulihkan switch sebelumnya terlebih dahulu.")
        active = self.detect()
        if active == "conflict":
            raise RuntimeError(
                "Status cache tidak jelas. Periksa backup sebelum menghapus."
            )
        path = self.active if active == pid else self.backup(pid)
        check_tree(path)
        # Reversible deletion: move outside the live cache folders.
        trash = os.path.join(self.data_dir, "cache-switcher-trash")
        if is_link(trash):
            raise RuntimeError("Folder pemulihan berupa symlink/junction")
        os.makedirs(trash, exist_ok=True)
        destination = os.path.join(trash, pid + "_" + str(time.time_ns()))
        before = self.snapshot()
        os.rename(path, destination)
        self.profiles.pop(pid)
        if active == pid:
            self.active_id = None
        try:
            self.save()
        except Exception:
            os.rename(destination, path)
            self.profiles = before["profiles"]
            self.active_id = before["active_id"]
            raise
        return destination


def folder_size(path):
    if not os.path.isdir(path) or is_link(path):
        return 0
    total = 0
    for root, dirs, files in os.walk(path, followlinks=False):
        dirs[:] = [d for d in dirs if not is_link(os.path.join(root, d))]
        for name in files:
            p = os.path.join(root, name)
            if not is_link(p):
                try:
                    total += os.path.getsize(p)
                except OSError:
                    pass
    return total


def format_size(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.1f} {unit}"
        n /= 1024


def clean_temp(paths):
    removed, skipped = 0, 0
    for folder in dict.fromkeys(os.path.abspath(p) for p in paths if p):
        if not os.path.isdir(folder) or is_link(folder):
            skipped += 1
            continue
        for name in os.listdir(folder):
            path = os.path.join(folder, name)
            try:
                runtime = getattr(sys, "_MEIPASS", None)
                if runtime and os.path.normcase(
                    os.path.abspath(path)
                ) == os.path.normcase(os.path.abspath(runtime)):
                    skipped += 1
                    continue
                # Leave junctions and linked trees alone.
                if is_link(path):
                    skipped += 1
                elif os.path.isdir(path):
                    linked = any(
                        is_link(os.path.join(r, d))
                        for r, ds, fs in os.walk(path)
                        for d in ds + fs
                    )
                    if linked:
                        skipped += 1
                    else:
                        shutil.rmtree(path)
                        removed += 1
                else:
                    os.remove(path)
                    removed += 1
            except OSError:
                skipped += 1
    return removed, skipped


def set_dns(adapter, choice):
    if os.name != "nt":
        raise RuntimeError("Pengaturan DNS hanya tersedia di Windows")
    if not ctypes.windll.shell32.IsUserAnAdmin():
        raise RuntimeError("Untuk DNS, buka aplikasi dengan Run as administrator.")
    common = ["netsh", "interface", "ipv4"]
    if choice == "Default (ISP)":
        commands = [common + ["set", "dnsservers", "name=" + adapter, "source=dhcp"]]
    else:
        primary, secondary = (
            ("1.1.1.1", "1.0.0.1") if choice == "Cloudflare" else ("8.8.8.8", "8.8.4.4")
        )
        commands = [
            common
            + [
                "set",
                "dnsservers",
                "name=" + adapter,
                "source=static",
                "address=" + primary,
                "validate=no",
            ],
            common
            + [
                "add",
                "dnsservers",
                "name=" + adapter,
                "address=" + secondary,
                "index=2",
                "validate=no",
            ],
        ]
    for cmd in commands:
        r = subprocess.run(
            cmd, capture_output=True, text=True, creationflags=0x08000000, timeout=30
        )
        if r.returncode:
            raise RuntimeError("Konfigurasi DNS gagal.\n" + r.stdout + r.stderr)
    subprocess.run(
        ["ipconfig", "/flushdns"],
        capture_output=True,
        creationflags=0x08000000,
        timeout=15,
    )
