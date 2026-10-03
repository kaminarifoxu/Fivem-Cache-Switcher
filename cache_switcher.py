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

VERSION = "2.3.2"
APP_NAME = "GanoV-Cache-Switch"
COPYRIGHT = "Copyright (c) 2026 GANOMABI / amiinarii"
PREFIX = "server-cache-priv_"
GITHUB_REPOSITORY = "kaminarifoxu/Fivem-Cache-Switcher"
RELEASES_URL = "https://github.com/" + GITHUB_REPOSITORY + "/releases"


def user_config_path():
    root = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), ".local", "share")
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
    if len(parts) != 3 or any(not p or not p.isascii() or not p.isdecimal() for p in parts):
        raise ValueError("Gunakan versi stabil seperti v2.3.0")
    return tuple(int(p) for p in parts)


def check_latest_release(current=VERSION):
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError
    request = Request("https://api.github.com/repos/" + GITHUB_REPOSITORY + "/releases/latest",
                      headers={"Accept": "application/vnd.github+json", "User-Agent": APP_NAME + "/" + current,
                               "X-GitHub-Api-Version": "2022-11-28"})
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
    return {"version": tag.removeprefix("v"), "url": url}


def open_release_page(url):
    if not url.startswith(RELEASES_URL + "/tag/"):
        raise ValueError("Alamat rilis tidak valid")
    if os.name == "nt":
        os.startfile(url)
    else:
        import webbrowser
        webbrowser.open(url)


def nearby_exe(path):
    for candidate in [os.path.join(path, "FiveM.exe"), os.path.join(os.path.dirname(path), "FiveM.exe")]:
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
        bases += [os.path.join(root, n) for n in os.listdir(root)
                  if os.path.isdir(os.path.join(root, n)) and not is_link(os.path.join(root, n))]
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
        elif (os.path.basename(base).lower() in ["fivem.app", "fivem application data"]
              or os.path.isdir(os.path.join(base, "citizen"))
              or any(n in names for n in ["server-cache", "game-storage", "nui-storage"])):
            normal.append(os.path.abspath(data))
    return list(dict.fromkeys(strong or normal))


def safe_id(value):
    return isinstance(value, str) and value and all(c in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in value)


def atomic_json(path, data):
    tmp = path + ".new"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def is_link(path):
    return os.path.islink(path) or (hasattr(os.path, "isjunction") and os.path.isjunction(path))


def check_tree(path):
    if is_link(path):
        raise RuntimeError("Folder adalah symlink/junction. Pilih folder cache biasa.")
    if not os.path.isdir(path):
        raise RuntimeError("Folder cache tidak ditemukan: " + path)


def no_fivem():
    if os.name != "nt":
        return
    result = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True,
                            text=True, creationflags=0x08000000, timeout=15, check=True)
    for line in result.stdout.splitlines():
        name = line.split('",')[0].strip('"').lower()
        if name == "fivem.exe" or (name.startswith("fivem_") and name.endswith(".exe")):
            raise RuntimeError("FiveM masih berjalan. Tutup FiveM sepenuhnya sebelum mengubah cache.")


class CacheStore:
    def __init__(self, config_path, default_path=None):
        self.config_path = config_path
        self.path = default_path or os.path.join(os.environ.get("LOCALAPPDATA", ""), "FiveM", "FiveM.app")
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
                if not isinstance(profiles, dict) or any(not safe_id(k) or not isinstance(v, str) for k, v in profiles.items()):
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
                self.active_id = data.get("active_id") if data.get("active_id") in profiles else None
            except Exception as e:
                self.load_warning = "Konfigurasi gagal dibaca; file asli tetap tersedia.\n" + str(e)
        if not self.exe:
            launcher = os.path.join(os.environ.get("LOCALAPPDATA", ""), "FiveM", "FiveM.exe")
            if os.path.isfile(launcher):
                self.exe = os.path.abspath(launcher)
                locations = find_data_directories(self.exe)
                if len(locations) == 1 and not self.profiles:
                    self.path = os.path.dirname(locations[0])

    def select_exe(self, exe, data_dir=None):
        no_fivem()
        if os.path.isfile(self.journal):
            raise RuntimeError("Pulihkan switch sebelumnya sebelum mengganti instalasi.")
        locations = find_data_directories(exe)
        if data_dir is None:
            if len(locations) != 1:
                raise RuntimeError("Folder data belum dapat ditentukan. Pilih folder data milik instalasi ini.")
            data_dir = locations[0]
        data_dir = os.path.abspath(data_dir)
        if os.path.basename(data_dir).lower() != "data" or not os.path.isdir(data_dir) or is_link(data_dir):
            raise RuntimeError("Pilih folder data yang valid.")
        before = self.snapshot()
        self.exe = os.path.abspath(exe)
        new_path = os.path.dirname(data_dir)
        changed = os.path.normcase(new_path) != os.path.normcase(os.path.abspath(self.path))
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
            pid = name[len(PREFIX):]
            path = os.path.join(self.data_dir, name)
            if safe_id(pid) and pid not in self.profiles and os.path.isdir(path) and not is_link(path):
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
        if not self.exe or not os.path.isfile(self.exe) or os.path.basename(self.exe).lower() != "fivem.exe":
            raise RuntimeError("Pilih FiveM.exe terlebih dahulu.")
        if not os.path.isdir(self.data_dir):
            raise RuntimeError("Folder data instalasi ini tidak ditemukan. Pilih ulang FiveM.exe.")
        if self.load_warning:
            raise RuntimeError(self.load_warning + "\nPerbaiki konfigurasi sebelum mengubah cache.")
        if is_link(self.data_dir):
            raise RuntimeError("Folder data berupa symlink/junction.")

    def snapshot(self):
        return {"fivem_exe": self.exe, "fivem_path": self.path, "profiles": dict(self.profiles), "active_id": self.active_id}

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
            raise RuntimeError("Beberapa backup tidak ditemukan. Periksa folder data; cache tidak akan ditebak.")
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
                raise RuntimeError("Backup tujuan sudah ada. Switch dibatalkan untuk menjaga data.")
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
                raise RuntimeError("Switch terhenti; data tetap disimpan. Klik Pulihkan Switch.\n" + str(recovery_error))
            raise

    def recover(self):
        no_fivem()
        self.validate()
        with open(self.journal, encoding="utf-8") as f:
            record = json.load(f)
        old, target, before = record.get("old"), record.get("target"), record.get("before")
        if not safe_id(target) or (old is not None and not safe_id(old)) or old == target:
            raise RuntimeError("Catatan pemulihan tidak valid")
        if not isinstance(before, dict) or os.path.normcase(before.get("fivem_path", "")) != os.path.normcase(self.path):
            raise RuntimeError("Path catatan pemulihan tidak cocok")
        profiles = before.get("profiles")
        if not isinstance(profiles, dict) or target not in profiles or any(not safe_id(k) or not isinstance(v, str) for k, v in profiles.items()):
            raise RuntimeError("Profil pemulihan tidak valid")
        # Locations determine which atomic rename completed, even after a crash.
        if os.path.isdir(self.active) and not os.path.lexists(self.backup(target)):
            check_tree(self.active)
            os.rename(self.active, self.backup(target))
        if old and os.path.isdir(self.backup(old)) and not os.path.lexists(self.active):
            check_tree(self.backup(old))
            os.rename(self.backup(old), self.active)
        if old and not os.path.isdir(self.active):
            raise RuntimeError("Cache sebelumnya tidak ditemukan. Periksa folder data secara manual.")
        if not os.path.isdir(self.backup(target)):
            raise RuntimeError("Backup target tidak ditemukan. Periksa folder data secara manual.")
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
            raise RuntimeError("Status cache tidak jelas. Periksa backup sebelum menghapus.")
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
                if runtime and os.path.normcase(os.path.abspath(path)) == os.path.normcase(os.path.abspath(runtime)):
                    skipped += 1
                    continue
                # Leave junctions and linked trees alone.
                if is_link(path):
                    skipped += 1
                elif os.path.isdir(path):
                    linked = any(is_link(os.path.join(r, d)) for r, ds, fs in os.walk(path) for d in ds + fs)
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
        primary, secondary = ("1.1.1.1", "1.0.0.1") if choice == "Cloudflare" else ("8.8.8.8", "8.8.4.4")
        commands = [common + ["set", "dnsservers", "name=" + adapter, "source=static", "address=" + primary, "validate=no"],
                    common + ["add", "dnsservers", "name=" + adapter, "address=" + secondary, "index=2", "validate=no"]]
    for cmd in commands:
        r = subprocess.run(cmd, capture_output=True, text=True, creationflags=0x08000000, timeout=30)
        if r.returncode:
            raise RuntimeError("Konfigurasi DNS gagal.\n" + r.stdout + r.stderr)
    subprocess.run(["ipconfig", "/flushdns"], capture_output=True, creationflags=0x08000000, timeout=15)



def main():
    import customtkinter as ctk
    from tkinter import messagebox, filedialog, PhotoImage, Label
    ctk.set_appearance_mode("dark")
    BG, CARD, LINE = "#0d0b0d", "#191518", "#3b292e"
    RED, GOLD, MUTED, WHITE = "#b82736", "#e9bc70", "#ad999f", "#f5ece3"
    FONT = "Segoe UI" if os.name == "nt" else "DejaVu Sans"
    base = os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))
    assets = os.path.join(getattr(sys, "_MEIPASS", base), "assets")

    class App(ctk.CTk):
        def __init__(self):
            super().__init__()
            self.withdraw()
            self.title(APP_NAME)
            self.geometry("1180x820")
            self.minsize(1040, 760)
            self.configure(fg_color=BG)
            self.store = None
            self.busy, self.closed = False, False
            self.results, self.buttons, self.images = [], [], {}
            self.sizes, self.raw_sizes = {}, {}
            self.size_generation = 0
            self.update_checking = False
            self.update_dialog = None
            self.page = "cache"
            self.protocol("WM_DELETE_WINDOW", self.close)
            try:
                self.iconbitmap(os.path.join(assets, "ganomabi.ico"))
            except Exception:
                pass
            self.show_startup_splash()
            self.after(100, self.initialize)

        def show_startup_splash(self):
            self.splash = ctk.CTkToplevel(self)
            self.splash.withdraw()
            self.splash.overrideredirect(True)
            self.splash.configure(fg_color=BG)
            scale = ctk.ScalingTracker.get_window_scaling(self.splash)
            x = (self.winfo_screenwidth() - round(540 * scale)) // 2
            y = (self.winfo_screenheight() - round(390 * scale)) // 2
            self.splash.geometry(f"540x390+{x}+{y}")
            frame = ctk.CTkFrame(self.splash, fg_color="#211219", border_color="#794336", border_width=1, corner_radius=16)
            frame.pack(fill="both", expand=True, padx=2, pady=2)
            self.art(frame, "sidebar", "#211219").pack(pady=(16, 0))
            ctk.CTkLabel(frame, text=APP_NAME, text_color=GOLD, font=(FONT, 20, "bold")).pack(pady=(8, 0))
            ctk.CTkLabel(frame, text="FiveM Launcher & Profiles", text_color=MUTED, font=(FONT, 12)).pack(pady=(0, 19))
            self.splash_progress = ctk.CTkProgressBar(frame, width=420, height=7, fg_color=LINE, progress_color=GOLD)
            self.splash_progress.pack()
            self.splash_progress.set(0.08)
            self.splash_status = ctk.CTkLabel(frame, text="Menyiapkan aplikasi...", text_color=MUTED, font=(FONT, 11))
            self.splash_status.pack(pady=10)
            ctk.CTkLabel(frame, text=COPYRIGHT, text_color=MUTED, font=(FONT, 9)).pack(pady=(0, 3))
            self.splash.deiconify()
            self.splash.lift()
            self.splash.attributes("-topmost", True)

        def initialize(self):
            try:
                self.splash_status.configure(text="Membaca konfigurasi dan lokasi FiveM...")
                self.splash_progress.set(0.25)
                self.update_idletasks()
                self.store = open_user_store(base)
                self.splash_status.configure(text="Menyiapkan profil kota dan tampilan...")
                self.splash_progress.set(0.55)
                self.update_idletasks()
                self.build_main_ui()
                self.splash_status.configure(text="Siap. Selamat datang di GANOMABI.")
                self.splash_progress.set(1)
                self.after(220, self.finish_startup)
            except Exception as e:
                self.splash.destroy()
                messagebox.showerror("Aplikasi gagal dibuka", str(e), parent=self)
                self.closed = True
                self.destroy()

        def finish_startup(self):
            self.splash.destroy()
            self.splash = None
            self.deiconify()
            self.lift()
            if self.store.load_warning:
                messagebox.showwarning("Konfigurasi", self.store.load_warning, parent=self)
            self.after(800, self.check_updates)

        def build_main_ui(self):
            self.grid_columnconfigure(1, weight=1)
            self.grid_rowconfigure(0, weight=1)
            side = ctk.CTkFrame(self, width=250, fg_color="#161014", corner_radius=0)
            side.grid(row=0, column=0, sticky="nsew")
            side.grid_propagate(False)
            self.art(side, "sidebar", "#161014").pack(pady=(15, 0))
            ctk.CTkLabel(side, text=APP_NAME, text_color=GOLD, font=(FONT, 16, "bold")).pack(pady=(0, 3))
            ctk.CTkLabel(side, text="FiveM Launcher & Profiles", text_color=MUTED, font=(FONT, 11)).pack(pady=(0, 22))
            self.nav = {}
            for key, text in [("cache", "Profil kota"), ("tools", "Peralatan")]:
                self.nav[key] = self.btn(side, text, lambda p=key: self.show_page(p), width=206)
                self.nav[key].pack(fill="x", padx=22, pady=4)
            ctk.CTkFrame(side, height=1, fg_color=LINE).pack(fill="x", padx=24, pady=21)
            self.btn(side, "Jalankan FiveM", self.launch, primary=True).pack(fill="x", padx=22, pady=(0, 7))
            self.btn(side, "Pilih FiveM.exe", self.change_path).pack(fill="x", padx=22, pady=3)
            self.exe_label = ctk.CTkLabel(side, text="", text_color=MUTED, font=(FONT, 10), wraplength=202, justify="left")
            self.exe_label.pack(anchor="w", padx=24, pady=10)
            self.btn(side, "Cek update", lambda: self.check_updates(manual=True)).pack(fill="x", padx=22, pady=(8, 0))
            self.update_status = ctk.CTkLabel(side, text="", text_color=MUTED, font=(FONT, 10), wraplength=202)
            self.update_status.pack(padx=24, pady=4)
            self.art(side, "mini", "#161014").pack(side="bottom", pady=(0, 3))
            ctk.CTkLabel(side, text=COPYRIGHT, text_color=MUTED, font=(FONT, 9), wraplength=210).pack(side="bottom", pady=(8, 0))
            ctk.CTkLabel(side, text="GANOMABI  /  v" + VERSION, text_color=GOLD, font=(FONT, 10, "bold")).pack(side="bottom", pady=(12, 0))

            body = ctk.CTkFrame(self, fg_color="transparent")
            body.grid(row=0, column=1, sticky="nsew", padx=24, pady=(20, 14))
            body.grid_columnconfigure(0, weight=1)
            body.grid_rowconfigure(0, weight=1)
            self.pages = {}
            for name in ["cache", "tools"]:
                page = ctk.CTkFrame(body, fg_color="transparent", corner_radius=0)
                page.grid(row=0, column=0, sticky="nsew")
                self.pages[name] = page
            self.build_cache(self.pages["cache"])
            self.build_tools(self.pages["tools"])
            footer = ctk.CTkFrame(body, fg_color="transparent", height=28)
            footer.grid(row=1, column=0, sticky="ew", pady=(8, 0))
            footer.grid_columnconfigure(0, weight=1)
            self.feedback = ctk.CTkLabel(footer, text="Siap. Pilih FiveM.exe untuk menghubungkan instalasimu.", anchor="w", text_color=MUTED, font=(FONT, 10), wraplength=690, justify="left")
            self.feedback.grid(row=0, column=0, sticky="ew")
            self.busy_bar = ctk.CTkProgressBar(footer, width=95, height=4, progress_color=GOLD, fg_color=LINE, mode="indeterminate")
            self.busy_bar.grid(row=0, column=1, padx=(10, 0))
            self.busy_bar.set(0)
            self.busy_bar.grid_remove()
            self.show_page("cache")
            self.refresh()
            if self.store.exe and os.path.isfile(self.store.exe):
                self.feedback.configure(text="Siap. Pilih kota yang ingin kamu aktifkan.")
            self.after(100, self.poll)
            self.after(250, self.load_adapters)

        def art(self, parent, name, background):
            scale = ctk.ScalingTracker.get_widget_scaling(self)
            suffix = "1" if scale <= 1.1 else "125" if scale <= 1.35 else "150" if scale <= 1.7 else "2"
            key = name + "_" + suffix
            if key not in self.images:
                self.images[key] = PhotoImage(master=self, file=os.path.join(assets, "ui", key + ".png"))
            return Label(parent, image=self.images[key], bg=background, bd=0, highlightthickness=0)

        def btn(self, parent, text, command, primary=False, width=150, height=38):
            def guarded():
                if not self.busy:
                    command()
            b = ctk.CTkButton(parent, text=text, command=guarded, width=width, height=height,
                             fg_color=RED if primary else "#292026", hover_color="#d13747" if primary else "#443139",
                             text_color=WHITE, border_color="#71333a" if primary else LINE,
                             border_width=1, corner_radius=9, font=(FONT, 12, "bold"))
            self.buttons.append(b)
            return b

        def show_page(self, name):
            if self.busy:
                return
            self.page = name
            for key, page in self.pages.items():
                if key == name:
                    page.grid()
                else:
                    page.grid_remove()
            for key, b in self.nav.items():
                b.configure(fg_color="#59222c" if key == name else "#292026", text_color=GOLD if key == name else WHITE)

        def build_cache(self, page):
            page.grid_columnconfigure(0, weight=1)
            page.grid_rowconfigure(3, weight=1)
            hero = ctk.CTkFrame(page, fg_color="#211219", border_color="#68303b", border_width=1, corner_radius=18, height=178)
            hero.grid(row=0, column=0, sticky="ew", pady=(0, 15))
            hero.grid_columnconfigure(0, weight=1)
            hero.grid_propagate(False)
            left = ctk.CTkFrame(hero, fg_color="transparent")
            left.grid(row=0, column=0, sticky="w", padx=(20, 0), pady=(0, 8))
            self.art(left, "hero", "#211219").pack(anchor="w")
            ctk.CTkLabel(left, text="SATU KOMUNITAS. BANYAK KOTA.", font=(FONT, 11, "bold"), text_color=GOLD).pack(anchor="w", padx=12, pady=(0, 3))
            self.art(hero, "hero_fox", "#211219").grid(row=0, column=1, padx=(4, 18), pady=12)
            summary = ctk.CTkFrame(page, fg_color=CARD, border_color=LINE, border_width=1, corner_radius=14)
            summary.grid(row=1, column=0, sticky="ew", pady=(0, 16))
            summary.grid_columnconfigure(1, weight=1)
            self.art(summary, "status", CARD).grid(row=0, column=0, padx=(12, 4), pady=10)
            text = ctk.CTkFrame(summary, fg_color="transparent")
            text.grid(row=0, column=1, sticky="ew", padx=8, pady=14)
            ctk.CTkLabel(text, text="CACHE AKTIF", text_color=MUTED, font=(FONT, 10, "bold"), anchor="w").pack(fill="x")
            self.status = ctk.CTkLabel(text, text="", font=(FONT, 19, "bold"), text_color=GOLD, anchor="w", wraplength=365, justify="left")
            self.status.pack(fill="x", pady=(3, 0))
            self.connection = ctk.CTkLabel(text, text="", text_color=MUTED, font=(FONT, 10), anchor="w")
            self.connection.pack(fill="x")
            stats = ctk.CTkFrame(summary, fg_color="transparent")
            stats.grid(row=0, column=2, padx=20, pady=15)
            self.metric_count = ctk.CTkLabel(stats, text="0 PROFIL", text_color=WHITE, font=(FONT, 13, "bold"))
            self.metric_count.pack(anchor="e")
            self.metric_size = ctk.CTkLabel(stats, text="0 B tersimpan", text_color=MUTED, font=(FONT, 10))
            self.metric_size.pack(anchor="e", pady=(4, 0))
            row = ctk.CTkFrame(page, fg_color="transparent")
            row.grid(row=2, column=0, sticky="ew", pady=(0, 10))
            self.count = ctk.CTkLabel(row, text="PROFIL KOTA", font=(FONT, 14, "bold"), text_color=WHITE)
            self.count.pack(side="left")
            self.btn(row, "+ Tambah kota", self.add, primary=True, width=142).pack(side="right")
            self.btn(row, "Refresh", self.refresh, width=90).pack(side="right", padx=8)
            self.list = ctk.CTkScrollableFrame(page, fg_color="transparent", corner_radius=0, scrollbar_button_color="#57353e", scrollbar_button_hover_color=RED)
            self.list.grid(row=3, column=0, sticky="nsew")
            self.path_label = ctk.CTkLabel(page, text="", anchor="w", text_color=MUTED, font=(FONT, 10), wraplength=780, justify="left")
            self.path_label.grid(row=4, column=0, sticky="ew", pady=(9, 0))
            ctk.CTkLabel(page, text="Tutup FiveM sebelum switch. Cache kota disimpan secara terpisah.", anchor="w", text_color="#ba927e", font=(FONT, 10)).grid(row=5, column=0, sticky="ew", pady=(2, 0))

        def build_tools(self, page):
            page.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(page, text="PERALATAN", font=(FONT, 27, "bold"), text_color=WHITE).grid(row=0, column=0, sticky="w", pady=(0, 4))
            ctk.CTkLabel(page, text="Kontrol instalasi, file sementara, dan jaringanmu.", text_color=MUTED, font=(FONT, 12)).grid(row=1, column=0, sticky="w", pady=(0, 22))
            card = ctk.CTkFrame(page, fg_color=CARD, border_width=1, border_color=LINE, corner_radius=15)
            card.grid(row=2, column=0, sticky="ew", pady=(0, 14))
            ctk.CTkLabel(card, text="INSTALASI & PEMULIHAN", font=(FONT, 14, "bold"), text_color=GOLD).pack(anchor="w", padx=20, pady=(18, 8))
            ctk.CTkLabel(card, text="Buka lokasi cache atau pulihkan switch yang belum selesai.", text_color=MUTED, font=(FONT, 11)).pack(anchor="w", padx=20)
            actions = ctk.CTkFrame(card, fg_color="transparent")
            actions.pack(fill="x", padx=20, pady=(12, 18))
            self.btn(actions, "Buka folder data", self.open_folder).pack(side="left")
            self.btn(actions, "Pulihkan Switch", self.recover).pack(side="left", padx=10)
            self.btn(actions, "Pilih FiveM.exe", self.change_path, primary=True).pack(side="right")
            temp = ctk.CTkFrame(page, fg_color=CARD, border_width=1, border_color=LINE, corner_radius=15)
            temp.grid(row=3, column=0, sticky="ew", pady=(0, 14))
            ctk.CTkLabel(temp, text="WINDOWS TEMP CLEANER", text_color=GOLD, font=(FONT, 14, "bold")).pack(anchor="w", padx=20, pady=(18, 7))
            ctk.CTkLabel(temp, text="Bersihkan file sementara. File terkunci akan dilewati.", text_color=MUTED, font=(FONT, 11)).pack(anchor="w", padx=20)
            tr = ctk.CTkFrame(temp, fg_color="transparent")
            tr.pack(fill="x", padx=20, pady=(12, 18))
            self.temp_choice = ctk.CTkOptionMenu(tr, values=["User Temp", "System Temp", "Semua Temp"], fg_color="#30222a", button_color="#6d2e3b", button_hover_color=RED, width=210, font=(FONT, 12))
            self.temp_choice.pack(side="left")
            self.btn(tr, "Bersihkan", self.clean, width=140).pack(side="right")
            dns = ctk.CTkFrame(page, fg_color=CARD, border_width=1, border_color=LINE, corner_radius=15)
            dns.grid(row=4, column=0, sticky="ew", pady=(0, 14))
            ctk.CTkLabel(dns, text="NETWORK DNS", text_color=GOLD, font=(FONT, 14, "bold")).pack(anchor="w", padx=20, pady=(18, 7))
            ctk.CTkLabel(dns, text="Pilih adapter. Pengaturan DNS memerlukan administrator.", text_color=MUTED, font=(FONT, 11)).pack(anchor="w", padx=20)
            dr = ctk.CTkFrame(dns, fg_color="transparent")
            dr.pack(fill="x", padx=20, pady=(12, 18))
            self.adapter = ctk.CTkOptionMenu(dr, values=["Pilih adapter"], width=230, fg_color="#30222a", button_color="#6d2e3b", button_hover_color=RED, font=(FONT, 12))
            self.adapter.pack(side="left")
            self.dns_choice = ctk.CTkOptionMenu(dr, values=["Default (ISP)", "Cloudflare", "Google"], width=165, fg_color="#30222a", button_color="#6d2e3b", button_hover_color=RED, font=(FONT, 12))
            self.dns_choice.pack(side="left", padx=12)
            self.btn(dr, "Terapkan DNS", self.dns, primary=True, width=140).pack(side="right")
            self.art(page, "tools", BG).grid(row=5, column=0, pady=(0, 0))

        def poll(self):
            while self.results:
                kind, value = self.results.pop(0)
                if kind == "update":
                    manual, release, error = value
                    self.update_checking = False
                    if error:
                        self.update_status.configure(text="Tidak dapat mengecek update.")
                        if manual:
                            self.show_update_notice(error=error)
                    elif release:
                        self.update_status.configure(text="Update tersedia: v" + release["version"])
                        self.show_update(release)
                    else:
                        self.update_status.configure(text="Belum ada versi yang lebih baru.")
                        if manual:
                            self.show_update_notice()
                elif kind == "sizes":
                    generation, sizes = value
                    if generation == self.size_generation and not self.busy:
                        self.raw_sizes = sizes
                        self.sizes = {p: format_size(n) if n is not None else "Backup tidak ditemukan" for p, n in sizes.items()}
                        self.render()
                elif kind == "adapters":
                    if value:
                        self.adapter.configure(values=value)
                        self.adapter.set(value[0])
                else:
                    self.busy = False
                    self.busy_bar.stop()
                    self.busy_bar.set(0)
                    self.busy_bar.grid_remove()
                    self.title(APP_NAME)
                    for b in self.buttons:
                        if b.winfo_exists():
                            b.configure(state="normal")
                    if kind == "error":
                        self.feedback.configure(text="Operasi gagal. Lihat pesan untuk detail.")
                        messagebox.showerror("Operasi gagal", str(value), parent=self)
                    else:
                        self.feedback.configure(text=str(value))
                    self.refresh()
            if not self.closed:
                self.after(100, self.poll)

        def check_updates(self, manual=False):
            if self.closed or self.update_checking:
                return
            self.update_checking = True
            self.update_status.configure(text="Mengecek update...")
            def worker():
                try:
                    result = (manual, check_latest_release(), None)
                except Exception as e:
                    result = (manual, None, str(e))
                self.results.append(("update", result))
            threading.Thread(target=worker, daemon=True).start()

        def show_update(self, release):
            self.show_update_notice(release=release)

        def show_update_notice(self, release=None, error=None):
            if self.closed:
                return
            if self.busy or self.grab_current() is not None:
                self.after(500, lambda: self.show_update_notice(release, error))
                return
            if self.update_dialog is not None and self.update_dialog.winfo_exists():
                self.update_dialog.lift()
                return
            dialog = self.update_dialog = ctk.CTkToplevel(self)
            dialog.withdraw()
            dialog.title("Pembaruan | " + APP_NAME)
            dialog.configure(fg_color=BG)
            dialog.resizable(False, False)
            dialog.transient(self)
            # Draw the complete header in the app theme, including its close button.
            dialog.overrideredirect(True)
            scale = ctk.ScalingTracker.get_window_scaling(dialog)
            x = self.winfo_rootx() + (self.winfo_width() - round(540 * scale)) // 2
            y = self.winfo_rooty() + (self.winfo_height() - round(460 * scale)) // 2
            dialog.geometry(f"540x460+{max(0, x)}+{max(0, y)}")
            def close(event=None):
                if dialog.winfo_exists():
                    if dialog.grab_current() == dialog:
                        dialog.grab_release()
                    dialog.destroy()
                self.update_dialog = None
            dialog.protocol("WM_DELETE_WINDOW", close)
            dialog.bind("<Escape>", close)
            shell = ctk.CTkFrame(dialog, fg_color=CARD, border_color="#79523c", border_width=1, corner_radius=0)
            shell.pack(fill="both", expand=True)
            header = ctk.CTkFrame(shell, fg_color="#21181c", height=48, corner_radius=0)
            header.pack(fill="x", padx=1, pady=(1, 0))
            header.pack_propagate(False)
            brand = ctk.CTkLabel(header, text="GANOMABI  /  PEMBARUAN", text_color=GOLD, font=(FONT, 11, "bold"))
            brand.pack(side="left", padx=22)
            ctk.CTkButton(header, text="×", width=36, height=30, corner_radius=6,
                          fg_color="transparent", hover_color=RED, text_color=MUTED,
                          font=(FONT, 22), command=close).pack(side="right", padx=10)
            drag = {}
            def start_drag(event):
                drag.update(x=event.x_root-dialog.winfo_x(), y=event.y_root-dialog.winfo_y())
            def move_drag(event):
                if drag:
                    dialog.geometry(f"+{max(0, event.x_root-drag['x'])}+{max(0, event.y_root-drag['y'])}")
            for widget in (header, brand):
                widget.bind("<ButtonPress-1>", start_drag)
                widget.bind("<B1-Motion>", move_drag)
            ctk.CTkFrame(shell, height=2, fg_color=RED, corner_radius=0).pack(fill="x", padx=1)
            head = ctk.CTkFrame(shell, fg_color="transparent")
            head.pack(fill="x", padx=26, pady=(18, 10))
            self.art(head, "status", CARD).pack(side="left", padx=(0, 16))
            titles = ctk.CTkFrame(head, fg_color="transparent")
            titles.pack(side="left", fill="x", expand=True)
            title = "Update tersedia" if release else "Cek update gagal" if error else "Versi kamu sudah terbaru"
            subtitle = "Versi baru siap diunduh." if release else "Coba lagi saat koneksi tersedia." if error else "Belum ada rilis stabil yang lebih baru."
            ctk.CTkLabel(titles, text=title, anchor="w", text_color=WHITE,
                         font=(FONT, 20, "bold")).pack(fill="x")
            ctk.CTkLabel(titles, text=subtitle, anchor="w", text_color=MUTED,
                         font=(FONT, 11)).pack(fill="x", pady=(4, 0))
            versions = ctk.CTkFrame(shell, fg_color="#100d10", border_color=LINE, border_width=1, corner_radius=10)
            versions.pack(fill="x", padx=26, pady=(0, 14))
            def version_cell(parent, label, value, color):
                cell = ctk.CTkFrame(parent, fg_color="transparent")
                cell.pack(side="left", fill="x", expand=True, padx=18, pady=12)
                ctk.CTkLabel(cell, text=label, text_color=MUTED, font=(FONT, 10), anchor="w").pack(fill="x")
                ctk.CTkLabel(cell, text=value, text_color=color, font=(FONT, 20, "bold"), anchor="w").pack(fill="x")
            version_cell(versions, "VERSI TERPASANG", "v" + VERSION, WHITE)
            version_cell(versions, "VERSI BARU" if release else "STATUS", "v" + release["version"] if release else "Offline" if error else "Terkini", GOLD)
            if release:
                description = "Unduh EXE dari GitHub, tutup aplikasi, lalu ganti EXE lama. Pengaturan dan profil kota tetap tersimpan otomatis."
            elif error:
                description = "GitHub belum dapat dihubungi. Periksa koneksi internet, lalu tekan Coba lagi. Aplikasi tetap dapat digunakan."
            else:
                description = "Kamu bisa melanjutkan menggunakan aplikasi. Kami akan memberi notifikasi ketika rilis baru tersedia di GitHub."
            ctk.CTkLabel(shell, text=description, text_color=MUTED, font=(FONT, 12),
                         justify="left", anchor="w", wraplength=480).pack(fill="x", padx=28, pady=(0, 10))
            ctk.CTkLabel(shell, text="© 2026 GANOMABI / amiinarii", text_color="#806b73",
                         font=(FONT, 10)).pack(side="bottom", pady=(0, 14))
            row = ctk.CTkFrame(shell, fg_color="transparent")
            row.pack(side="bottom", fill="x", padx=26, pady=(6, 12))
            def download():
                try:
                    open_release_page(release["url"])
                    close()
                except Exception as exc:
                    close()
                    self.show_update_notice(error=str(exc))
            def retry():
                close()
                self.check_updates(manual=True)
            action = download if release else retry if error else close
            label = "Unduh update" if release else "Coba lagi" if error else "Mengerti"
            primary = ctk.CTkButton(row, text=label, command=action, width=180, height=42,
                                    fg_color=RED, hover_color="#d13747", text_color=WHITE,
                                    corner_radius=9, font=(FONT, 12, "bold"))
            primary.pack(side="right")
            if release or error:
                ctk.CTkButton(row, text="Nanti" if release else "Tutup", command=close, width=120, height=42,
                              fg_color="#292026", hover_color="#443139", text_color=WHITE,
                              border_color=LINE, border_width=1, corner_radius=9,
                              font=(FONT, 12, "bold")).pack(side="right", padx=(0, 10))
            dialog.bind("<Return>", lambda event: action())
            dialog.deiconify()
            dialog.lift()
            dialog.grab_set()
            primary.focus_set()

        def run(self, label, work):
            if self.busy:
                return
            self.busy = True
            self.size_generation += 1
            self.feedback.configure(text=label)
            self.busy_bar.grid()
            self.busy_bar.start()
            for b in self.buttons:
                if b.winfo_exists():
                    b.configure(state="disabled")
            def worker():
                try:
                    self.results.append(("done", work() or "Selesai."))
                except Exception as e:
                    self.results.append(("error", str(e)))
            threading.Thread(target=worker, daemon=True).start()

        def render(self):
            for w in self.list.winfo_children():
                w.destroy()
            self.buttons = [b for b in self.buttons if b.winfo_exists()]
            active = self.store.detect()
            labels = {None: "Belum ada cache aktif", "external": "Cache lama belum terdaftar", "conflict": "Backup perlu diperiksa"}
            self.status.configure(text=self.store.profiles.get(active, labels.get(active, "Belum diketahui")), text_color=GOLD)
            if os.path.isfile(self.store.journal):
                self.status.configure(text="Switch perlu dipulihkan")
            linked = bool(self.store.exe and os.path.isfile(self.store.exe) and os.path.isdir(self.store.data_dir))
            self.connection.configure(text="Instalasi terhubung" if linked else "Pilih FiveM.exe untuk mulai")
            self.metric_count.configure(text=f"{len(self.store.profiles)} PROFIL")
            total = sum(n for n in self.raw_sizes.values() if n is not None)
            self.metric_size.configure(text=format_size(total) + " tersimpan")
            self.count.configure(text=f"PROFIL KOTA  /  {len(self.store.profiles):02d}")
            if not self.store.profiles:
                empty = ctk.CTkFrame(self.list, fg_color=CARD, border_color=LINE, border_width=1, corner_radius=14)
                empty.pack(fill="x", pady=6)
                self.art(empty, "empty", CARD).pack(pady=(18, 3))
                ctk.CTkLabel(empty, text="Perjalanan baru dimulai di sini.", text_color=WHITE, font=(FONT, 16, "bold")).pack()
                ctk.CTkLabel(empty, text="Pilih FiveM.exe, lalu tambahkan kota pertamamu.", text_color=MUTED, font=(FONT, 11)).pack(pady=(5, 20))
            for index, (pid, name) in enumerate(self.store.profiles.items()):
                current = active == pid
                bg = "#28191d" if current else CARD
                card = ctk.CTkFrame(self.list, fg_color=bg, border_color="#b68b48" if current else LINE, border_width=1, corner_radius=12)
                card.pack(fill="x", pady=(0, 9))
                badge = ctk.CTkFrame(card, fg_color="#56202b" if current else "#2b2227", width=46, height=46, corner_radius=12)
                badge.pack(side="left", padx=(16, 10), pady=15)
                badge.pack_propagate(False)
                ctk.CTkLabel(badge, text=f"{index + 1:02d}", font=(FONT, 16, "bold"), text_color=GOLD).pack(expand=True)
                info = ctk.CTkFrame(card, fg_color="transparent")
                info.pack(side="left", fill="x", expand=True, padx=(0, 8), pady=13)
                short = name if len(name) <= 30 else name[:27] + "..."
                ctk.CTkLabel(info, text=short, anchor="w", font=(FONT, 15, "bold"), text_color=WHITE).pack(fill="x")
                ctk.CTkLabel(info, text=("AKTIF  /  " if current else "TERSIMPAN  /  ") + self.sizes.get(pid, "Menghitung..."), anchor="w", text_color=GOLD if current else MUTED, font=(FONT, 10)).pack(fill="x", pady=(2, 0))
                actions = ctk.CTkFrame(card, fg_color="transparent")
                actions.pack(side="right", padx=13)
                switch = self.btn(actions, "Sedang aktif" if current else "Aktifkan", lambda p=pid: self.switch(p), primary=not current, width=106, height=35)
                switch.pack(side="left", padx=(0, 8))
                if current:
                    switch.configure(state="disabled", text_color_disabled=GOLD)
                self.btn(actions, "Nama", lambda p=pid: self.rename(p), width=56, height=35).pack(side="left", padx=(0, 5))
                self.btn(actions, "Hapus", lambda p=pid: self.delete(p), width=56, height=35).pack(side="left")
            if self.busy:
                for b in self.buttons:
                    if b.winfo_exists():
                        b.configure(state="disabled")

        def refresh(self):
            if self.busy:
                return
            self.exe_label.configure(text=self.store.exe or "FiveM.exe belum dipilih")
            self.path_label.configure(text="CACHE  /  " + self.store.active if self.store.exe else "CACHE  /  menunggu lokasi FiveM.exe")
            self.size_generation += 1
            generation = self.size_generation
            active = self.store.detect()
            paths = {p: self.store.active if p == active else self.store.backup(p) for p in self.store.profiles}
            self.sizes, self.raw_sizes = {}, {}
            self.render()
            def worker():
                sizes = {p: folder_size(path) if os.path.isdir(path) else None for p, path in paths.items()}
                self.results.append(("sizes", (generation, sizes)))
            threading.Thread(target=worker, daemon=True).start()

        def add(self):
            try:
                self.store.validate()
            except Exception as e:
                messagebox.showinfo("Hubungkan FiveM", str(e), parent=self)
                self.change_path()
                return
            name = self.ask_profile("Tambah kota / cache", "Nama kota atau profil cache", confirm="Tambah kota")
            if name and name.strip():
                self.run("Membuat profil...", lambda: (self.store.add(name.strip()), "Profil dibuat.")[1])

        def rename(self, pid):
            name = self.ask_profile("Ubah nama profil", "Nama kota atau profil cache", initial=self.store.profiles[pid], confirm="Simpan nama")
            if name and name.strip():
                self.run("Menyimpan nama...", lambda: (self.store.rename(pid, name.strip()), "Nama diperbarui.")[1])

        def ask_profile(self, title, prompt, initial="", confirm="Simpan"):
            dialog = ctk.CTkToplevel(self)
            dialog.withdraw()
            dialog.title(title + " | " + APP_NAME)
            dialog.configure(fg_color=BG)
            dialog.resizable(False, False)
            dialog.transient(self)
            dialog.result = None
            try:
                dialog.iconbitmap(os.path.join(assets, "ganomabi.ico"))
            except Exception:
                pass
            scale = ctk.ScalingTracker.get_window_scaling(dialog)
            x = self.winfo_rootx() + (self.winfo_width() - round(520 * scale)) // 2
            y = self.winfo_rooty() + (self.winfo_height() - round(360 * scale)) // 2
            dialog.geometry(f"520x360+{max(0, x)}+{max(0, y)}")
            card = ctk.CTkFrame(dialog, fg_color=CARD, border_color=LINE, border_width=1, corner_radius=14)
            card.pack(fill="both", expand=True, padx=12, pady=12)
            head = ctk.CTkFrame(card, fg_color="transparent")
            head.pack(fill="x", padx=20, pady=(10, 2))
            self.art(head, "status", CARD).pack(side="left", padx=(0, 12))
            titles = ctk.CTkFrame(head, fg_color="transparent")
            titles.pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(titles, text=APP_NAME, text_color=GOLD, font=(FONT, 10, "bold"), anchor="w").pack(fill="x")
            ctk.CTkLabel(titles, text=title, text_color=WHITE, font=(FONT, 20, "bold"), anchor="w").pack(fill="x", pady=4)
            ctk.CTkLabel(card, text=prompt, text_color=MUTED, font=(FONT, 12), anchor="w").pack(fill="x", padx=24, pady=(8, 5))
            entry = ctk.CTkEntry(card, height=44, fg_color="#100d10", border_color="#8e6846", border_width=1,
                                 corner_radius=9, text_color=WHITE, placeholder_text="Contoh: GANOMABI City",
                                 placeholder_text_color="#806b73", font=(FONT, 14))
            entry.pack(fill="x", padx=24)
            if initial:
                entry.insert(0, initial)
            hint = ctk.CTkLabel(card, text="Setiap kota memiliki cache yang terpisah.", text_color=MUTED, font=(FONT, 11), anchor="w")
            hint.pack(fill="x", padx=24, pady=(7, 10))
            buttons = ctk.CTkFrame(card, fg_color="transparent")
            buttons.pack(fill="x", padx=24, pady=(0, 18))
            def submit(event=None):
                name = entry.get().strip()
                if not name:
                    hint.configure(text="Isi nama kota terlebih dahulu.", text_color="#ee7782")
                    entry.focus_set()
                    return
                dialog.result = name
                dialog.destroy()
            self.btn(buttons, confirm, submit, primary=True, width=158, height=40).pack(side="right")
            self.btn(buttons, "Batal", dialog.destroy, width=110, height=40).pack(side="right", padx=9)
            dialog.bind("<Return>", submit)
            dialog.bind("<Escape>", lambda e: dialog.destroy())
            dialog.deiconify()
            dialog.wait_visibility()
            dialog.grab_set()
            dialog.after(80, lambda: (entry.focus_set(), entry.select_range(0, "end")) if initial else entry.focus_set())
            self.wait_window(dialog)
            return dialog.result

        def switch(self, pid):
            name = self.store.profiles[pid]
            self.run("Mengaktifkan " + name + "...", lambda: (self.store.switch(pid), "Cache aktif: " + name)[1])

        def delete(self, pid):
            if messagebox.askyesno("Hapus profil", "Hapus profil '" + self.store.profiles[pid] + "'?\n\nCache dipindahkan ke cache-switcher-trash dan bisa dipulihkan manual.", parent=self):
                self.run("Memindahkan cache...", lambda: "Cache disimpan di: " + self.store.delete(pid))

        def change_path(self):
            exe = filedialog.askopenfilename(title="Pilih FiveM.exe", initialdir=os.path.dirname(self.store.exe) if self.store.exe else os.path.expanduser("~"), filetypes=[("FiveM Launcher", "FiveM.exe"), ("Executable", "*.exe")], parent=self)
            if not exe:
                return
            try:
                no_fivem()
                locations = find_data_directories(exe)
                if len(locations) == 1:
                    data = locations[0]
                else:
                    messagebox.showinfo("Pilih lokasi data", "Ada beberapa lokasi data atau folder data belum terdeteksi.\nPilih folder data yang berisi server-cache-priv milik FiveM ini.", parent=self)
                    data = filedialog.askdirectory(title="Pilih folder data milik FiveM ini", initialdir=os.path.dirname(exe), parent=self)
                    if not data:
                        return
                if (self.store.profiles and os.path.normcase(os.path.dirname(os.path.abspath(data))) != os.path.normcase(os.path.abspath(self.store.path))
                    and not messagebox.askyesno("Ganti instalasi", "Tampilkan profil milik instalasi yang baru?\nCache instalasi sebelumnya tetap tersedia di folder asal.", parent=self)):
                    return
                self.run("Menghubungkan FiveM.exe...", lambda: (self.store.select_exe(exe, data), "FiveM terhubung. Backup kota yang ditemukan ditampilkan.")[1])
            except Exception as e:
                messagebox.showerror("Lokasi FiveM", str(e), parent=self)

        def open_folder(self):
            if os.path.isdir(self.store.data_dir) and self.store.exe:
                os.startfile(self.store.data_dir)
            else:
                self.change_path()

        def launch(self):
            if self.store.exe and os.path.isfile(self.store.exe):
                try:
                    os.startfile(self.store.exe)
                except OSError as e:
                    messagebox.showerror("Launch gagal", str(e), parent=self)
            else:
                self.change_path()

        def recover(self):
            if not os.path.isfile(self.store.journal):
                messagebox.showinfo("Pemulihan", "Tidak ada switch yang perlu dipulihkan.", parent=self)
                return
            self.run("Memulihkan switch...", lambda: (self.store.recover(), "Cache sebelumnya dipulihkan.")[1])

        def clean(self):
            choice = self.temp_choice.get()
            user = os.environ.get("TEMP", "")
            system = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "Temp")
            paths = [user] if choice == "User Temp" else [system] if choice == "System Temp" else [user, system]
            if messagebox.askyesno("Bersihkan Temp", "Hapus isi folder berikut?\n\n" + "\n".join(paths) + "\n\nFile yang dipakai atau terkunci akan dilewati.", parent=self):
                def work():
                    removed, skipped = clean_temp(paths)
                    return f"Temp: {removed} item dibersihkan, {skipped} dilewati."
                self.run("Membersihkan Temp...", work)

        def load_adapters(self):
            def worker():
                try:
                    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", "Get-NetAdapter | Where-Object Status -eq 'Up' | Select-Object -ExpandProperty Name"], capture_output=True, text=True, creationflags=0x08000000, timeout=20)
                    if r.returncode == 0:
                        self.results.append(("adapters", [n.strip() for n in r.stdout.splitlines() if n.strip()]))
                except Exception:
                    pass
            threading.Thread(target=worker, daemon=True).start()

        def dns(self):
            adapter, choice = self.adapter.get(), self.dns_choice.get()
            if adapter == "Pilih adapter":
                messagebox.showinfo("Adapter", "Tidak ada adapter aktif yang terdeteksi.", parent=self)
                self.load_adapters()
                return
            if messagebox.askyesno("Ubah DNS", f"Terapkan {choice} pada adapter '{adapter}'?", parent=self):
                self.run("Mengatur DNS...", lambda: (set_dns(adapter, choice), f"DNS {choice} diterapkan ke {adapter}.")[1])

        def close(self):
            if self.busy:
                messagebox.showinfo("Sedang bekerja", "Tunggu operasi selesai sebelum menutup aplikasi.", parent=self)
                return
            self.closed = True
            self.destroy()

    mutex = None
    if os.name == "nt":
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateMutexW.restype = ctypes.c_void_p
        kernel.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p]
        mutex = kernel.CreateMutexW(None, False, "Local\\FiveMCacheSwitcherRemake")
        if ctypes.get_last_error() == 183:
            messagebox.showinfo(APP_NAME, "Aplikasi sudah terbuka.")
            return
    app = App()
    app.mainloop()
    if mutex:
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        kernel.CloseHandle(mutex)


if __name__ == "__main__":
    main()
