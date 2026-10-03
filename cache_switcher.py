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

VERSION = "2.7.0"
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
    from auto_updater import release_asset
    return {"version": tag.removeprefix("v"), "url": url, **release_asset(release, GITHUB_REPOSITORY)}


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
    from tkinter import messagebox, filedialog, PhotoImage, Label, Canvas
    import i18n
    from i18n import tr
    from server_catalog import load_catalog, sync_catalog, connect_uri
    from server_status import fetch_statuses, page_url
    ui_settings_path = os.path.join(os.path.dirname(user_config_path()), 'ui_settings.json')
    i18n.load(ui_settings_path)
    ctk.set_appearance_mode('light')
    BG, CARD, LINE = ('#f7f0e3', '#fffaf1', '#ddc8a3')
    RED, GOLD, MUTED, WHITE = ('#b82736', '#896019', '#786757', '#30251e')
    FONT = 'Segoe UI' if os.name == 'nt' else 'DejaVu Sans'
    base = os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__))
    assets = os.path.join(getattr(sys, '_MEIPASS', base), 'assets')

    class App(ctk.CTk):

        def __init__(self):
            super().__init__()
            self.withdraw()
            self.title(APP_NAME)
            self.geometry('1180x820')
            self.minsize(1040, 760)
            self.configure(fg_color=BG)
            self.store = None
            self.busy, self.closed = (False, False)
            self.results, self.buttons, self.images = ([], [], {})
            self.sizes, self.raw_sizes = ({}, {})
            self.size_generation = 0
            self.update_checking = False
            self.update_installing = False
            self.update_dialog = None
            self.latest_release = None
            self.page = 'cache'
            self.ui_started = False
            self.catalog_syncing = False
            self.server_statuses = {}
            self.status_syncing = False
            self.server_page = 0
            self.catalog_cache = os.path.join(os.path.dirname(user_config_path()), 'servers_cache.json')
            self.catalog = load_catalog(self.catalog_cache, os.path.join(getattr(sys, '_MEIPASS', base), 'servers.json'))
            self.protocol('WM_DELETE_WINDOW', self.close)
            try:
                self.iconbitmap(os.path.join(assets, 'ganomabi.ico'))
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
            self.splash.geometry(f'540x390+{x}+{y}')
            frame = ctk.CTkFrame(self.splash, fg_color='#211219', border_color='#794336', border_width=1, corner_radius=16)
            frame.pack(fill='both', expand=True, padx=2, pady=2)
            self.art(frame, 'sidebar', '#211219').pack(pady=(16, 0))
            ctk.CTkLabel(frame, text=APP_NAME, text_color=GOLD, font=(FONT, 20, 'bold')).pack(pady=(8, 0))
            ctk.CTkLabel(frame, text='FiveM Launcher & Profiles', text_color=MUTED, font=(FONT, 12)).pack(pady=(0, 19))
            self.splash_progress = ctk.CTkProgressBar(frame, width=420, height=7, fg_color=LINE, progress_color=GOLD)
            self.splash_progress.pack()
            self.splash_progress.set(0.08)
            self.splash_status = ctk.CTkLabel(frame, text=tr('Menyiapkan aplikasi...'), text_color=MUTED, font=(FONT, 11))
            self.splash_status.pack(pady=10)
            ctk.CTkLabel(frame, text=COPYRIGHT, text_color=MUTED, font=(FONT, 9)).pack(pady=(0, 3))
            self.splash.deiconify()
            self.splash.lift()
            self.splash.attributes('-topmost', True)

        def initialize(self):
            try:
                self.splash_status.configure(text=tr('Membaca konfigurasi dan lokasi FiveM...'))
                self.splash_progress.set(0.25)
                self.update_idletasks()
                self.store = open_user_store(base)
                self.splash_status.configure(text=tr('Menyiapkan profil kota dan tampilan...'))
                self.splash_progress.set(0.55)
                self.update_idletasks()
                self.build_main_ui()
                self.splash_status.configure(text=tr('Siap. Selamat datang di GANOMABI.'))
                self.splash_progress.set(1)
                self.after(220, self.finish_startup)
            except Exception as e:
                self.splash.destroy()
                messagebox.showerror(tr('Aplikasi gagal dibuka'), str(e), parent=self)
                self.closed = True
                self.destroy()

        def finish_startup(self):
            self.splash.destroy()
            self.splash = None
            self.deiconify()
            self.lift()
            if self.store.load_warning:
                messagebox.showwarning(tr('Konfigurasi'), self.store.load_warning, parent=self)
            self.after(800, self.check_updates)

        def build_main_ui(self):
            self.grid_columnconfigure(1, weight=1)
            self.grid_rowconfigure(0, weight=1)
            side = ctk.CTkFrame(self, width=220, fg_color='#efe0c7', corner_radius=0)
            side.grid_propagate(False)
            self.sidebar = side
            side.grid(row=0, column=0, sticky='nsew')
            brand = self.art(side, 'mini', '#efe0c7')
            scale = ctk.ScalingTracker.get_widget_scaling(self)
            suffix = '1' if scale <= 1.1 else '125' if scale <= 1.35 else '150' if scale <= 1.7 else '2'
            self.images['compact_brand'] = self.images['mini_' + suffix].subsample(2, 2)
            brand.configure(image=self.images['compact_brand'])
            brand.pack(pady=(24, 8))
            ctk.CTkLabel(side, text=APP_NAME, text_color=GOLD, font=(FONT, 16, 'bold')).pack(pady=(0, 3))
            ctk.CTkLabel(side, text='FiveM Launcher & Profiles', text_color=MUTED, font=(FONT, 11)).pack(pady=(0, 22))
            self.nav = {}
            for key, text in [('cache', tr('Profil kota')), ('servers', tr('Daftar server')), ('tools', tr('Peralatan'))]:
                self.nav[key] = self.btn(side, text, lambda p=key: self.show_page(p), width=180)
                self.nav[key].pack(fill='x', padx=22, pady=4)
            ctk.CTkFrame(side, height=1, fg_color=LINE).pack(fill='x', padx=24, pady=21)
            self.btn(side, tr('Jalankan FiveM'), self.launch, primary=True).pack(fill='x', padx=22, pady=(0, 7))
            links = ctk.CTkFrame(side, fg_color='transparent')
            links.pack(fill='x', padx=22, pady=(2, 6))
            self.btn(links, 'GitHub', lambda: self.open_link('https://github.com/' + GITHUB_REPOSITORY), width=98, height=34).pack(side='left')
            self.btn(links, tr('Donasi'), lambda: self.open_link('https://saweria.co/itsaminarii'), primary=True, width=98, height=34).pack(side='right')
            ctk.CTkLabel(side, text=COPYRIGHT, text_color=MUTED, font=(FONT, 9), wraplength=210).pack(side='bottom', pady=(8, 0))
            ctk.CTkLabel(side, text='GANOMABI  /  v' + VERSION, text_color=GOLD, font=(FONT, 10, 'bold')).pack(side='bottom', pady=(12, 0))
            body = ctk.CTkFrame(self, fg_color='transparent')
            body.grid(row=0, column=1, sticky='nsew', padx=24, pady=(20, 14))
            body.grid_columnconfigure(0, weight=1)
            body.grid_rowconfigure(0, weight=1)
            self.pages = {}
            for name in ['cache', 'servers', 'tools']:
                page = ctk.CTkScrollableFrame(body, fg_color='transparent', corner_radius=0) if name == 'tools' else ctk.CTkFrame(body, fg_color='transparent', corner_radius=0)
                page.grid(row=0, column=0, sticky='nsew')
                self.pages[name] = page
            self.build_cache(self.pages['cache'])
            self.build_tools(self.pages['tools'])
            self.build_servers(self.pages['servers'])
            footer = ctk.CTkFrame(body, fg_color='transparent', height=28)
            footer.grid(row=1, column=0, sticky='ew', pady=(8, 0))
            footer.grid_columnconfigure(0, weight=1)
            self.feedback = ctk.CTkLabel(footer, text=tr('Siap. Pilih FiveM.exe untuk menghubungkan instalasimu.'), anchor='w', text_color=MUTED, font=(FONT, 10), wraplength=690, justify='left')
            self.feedback.grid(row=0, column=0, sticky='ew')
            self.busy_bar = ctk.CTkProgressBar(footer, width=95, height=4, progress_color=GOLD, fg_color=LINE, mode='indeterminate')
            self.busy_bar.grid(row=0, column=1, padx=(10, 0))
            self.busy_bar.set(0)
            self.busy_bar.grid_remove()
            self.update_banner = ctk.CTkFrame(footer, fg_color=CARD, corner_radius=6)
            self.update_banner.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(8, 0))
            self.update_banner.grid_columnconfigure(0, weight=1)
            self.global_update_label = ctk.CTkLabel(self.update_banner, text='', text_color=GOLD, font=(FONT, 11), anchor='w')
            self.global_update_label.grid(row=0, column=0, sticky='ew', padx=12, pady=8)
            self.global_update_button = ctk.CTkButton(self.update_banner, text=tr('Update sekarang'), command=lambda: self.show_update(self.latest_release) if self.latest_release else None, width=150, height=30, fg_color=RED, hover_color='#cf3444', text_color='#ffffff', font=(FONT, 11))
            self.global_update_button.grid(row=0, column=1, padx=10, pady=8)
            self.global_update_progress = ctk.CTkProgressBar(self.update_banner, height=4, progress_color=RED, fg_color=LINE)
            self.global_update_progress.grid(row=1, column=0, columnspan=2, sticky='ew', padx=12, pady=(0, 10))
            self.global_update_progress.set(0)
            self.global_update_progress.grid_remove()
            self.update_banner.grid_remove()
            self.show_page('cache')
            self.refresh()
            if self.latest_release:
                self.set_update_status(tr('Update tersedia: v') + self.latest_release['version'])
            if self.store.exe and os.path.isfile(self.store.exe):
                self.feedback.configure(text=tr('Siap. Pilih kota yang ingin kamu aktifkan.'))
            if not self.ui_started:
                self.ui_started = True
                self.after(100, self.poll)
                self.after(250, self.load_adapters)
                self.after(500, self.periodic_servers)
                self.after(1000, self.periodic_status)

        def change_language(self, choice):
            if self.busy or self.update_installing or self.grab_current() is not None:
                self.language_selector.set('English' if i18n.LANGUAGE == 'en' else 'Indonesia')
                return
            page = self.page
            try:
                i18n.set_language('en' if choice == 'English' else 'id', ui_settings_path)
            except OSError as exc:
                messagebox.showerror(tr('Konfigurasi'), str(exc), parent=self)
                return
            for widget in self.winfo_children():
                widget.destroy()
            self.buttons = []
            self.build_main_ui()
            self.show_page(page)

        def build_servers(self, page):
            page.grid_columnconfigure(0, weight=1)
            page.grid_rowconfigure(3, weight=1)
            ctk.CTkLabel(page, text=tr('List server'), font=(FONT, 24, 'bold'), text_color=WHITE).grid(row=0, column=0, sticky='w')
            ctk.CTkLabel(page, text=tr('Pilih server dan hubungkan melalui FiveM.'), font=(FONT, 12), text_color=MUTED, wraplength=800, justify='left').grid(row=1, column=0, sticky='w', pady=(4, 16))
            row = ctk.CTkFrame(page, fg_color='transparent')
            row.grid(row=2, column=0, sticky='ew', pady=(0, 14))
            self.catalog_status = ctk.CTkLabel(row, text='', font=(FONT, 11), text_color=MUTED)
            self.catalog_status.pack(side='left')
            self.btn(row, tr('Sync server'), self.sync_servers, width=130).pack(side='right')
            self.server_list = ctk.CTkFrame(page, fg_color='transparent')
            for column in range(3):
                self.server_list.grid_columnconfigure(column, weight=1, uniform='server')
            for row_index in range(3):
                self.server_list.grid_rowconfigure(row_index, weight=1, uniform='server')
            self.server_list.grid(row=3, column=0, sticky='nsew')
            pager = ctk.CTkFrame(page, fg_color='transparent')
            pager.grid(row=4, column=0, sticky='ew', pady=(10, 0))
            self.btn(pager, tr('Sebelumnya'), lambda: self.change_server_page(-1), width=110, height=30).pack(side='left')
            self.server_page_label = ctk.CTkLabel(pager, text='', text_color=MUTED, font=(FONT, 11))
            self.server_page_label.pack(side='left', expand=True)
            self.btn(pager, tr('Berikutnya'), lambda: self.change_server_page(1), width=110, height=30).pack(side='right')
            self.render_servers()

        def change_server_page(self, step):
            total = max(1, (len(self.catalog['servers']) + 8) // 9)
            self.server_page = min(total - 1, max(0, self.server_page + step))
            self.render_servers()

        def render_servers(self):
            for widget in self.server_list.winfo_children():
                widget.destroy()
            self.buttons = [button for button in self.buttons if button.winfo_exists()]
            total = max(1, (len(self.catalog['servers']) + 8) // 9)
            self.server_page = min(self.server_page, total - 1)
            self.server_page_label.configure(text=f"{self.server_page + 1} / {total}  •  {len(self.catalog['servers'])} server")
            servers = self.catalog['servers'][self.server_page * 9:(self.server_page + 1) * 9]
            for index, server in enumerate(servers):
                card = ctk.CTkFrame(self.server_list, fg_color=CARD, border_width=1, border_color=LINE, corner_radius=12)
                card.grid(row=index // 3, column=index % 3, sticky='nsew', padx=5, pady=5)
                card.grid_columnconfigure(0, weight=1)
                card.grid_rowconfigure(1, weight=1)
                name = server['name']
                if len(name) > 29:
                    name = name[:26] + '…'
                ctk.CTkLabel(card, text=name, height=20, text_color=WHITE, font=(FONT, 12, 'bold'), anchor='w').grid(row=0, column=0, sticky='ew', padx=12, pady=(10, 0))
                status = self.server_statuses.get(server['join_code'], {})
                description = status.get('description') or server.get('description', {}).get(i18n.LANGUAGE, '')
                description = description.replace('\n', ' ')
                if len(description) > 55:
                    description = description[:52] + '…'
                ctk.CTkLabel(card, text=description, height=26, text_color=MUTED, font=(FONT, 10), wraplength=195, justify='left', anchor='w').grid(row=1, column=0, sticky='nw', padx=12, pady=3)
                players = f"{status['clients']} / {status['maximum']} " + tr('pemain') if status.get('available') else tr('Belum tersedia')
                ctk.CTkLabel(card, text=players, height=18, text_color=GOLD, font=(FONT, 11, 'bold'), anchor='w').grid(row=2, column=0, sticky='ew', padx=12, pady=3)
                actions = ctk.CTkFrame(card, fg_color='transparent')
                actions.grid(row=3, column=0, sticky='ew', padx=10, pady=(3, 10))
                actions.grid_columnconfigure((0, 1), weight=1)
                self.btn(actions, tr('Halaman'), lambda code=server['join_code']: self.open_link(page_url(code)), width=75, height=28).grid(row=0, column=0, sticky='ew', padx=(0, 4))
                self.btn(actions, tr('Hubungkan'), lambda code=server['join_code']: self.connect_server(code), primary=True, width=85, height=28).grid(row=0, column=1, sticky='ew')
            if not self.catalog['servers']:
                ctk.CTkLabel(self.server_list, text=tr('Tidak ada server dalam daftar.'), text_color=MUTED).grid(row=0, column=0, columnspan=3, pady=30)

        def periodic_status(self):
            if self.closed:
                return
            if self.page == 'servers' or not self.server_statuses:
                self.refresh_server_status()
            self.after(60000, self.periodic_status)

        def refresh_server_status(self):
            if self.closed or self.status_syncing:
                return
            self.status_syncing = True
            codes = [server['join_code'] for server in self.catalog['servers']]
            def worker():
                self.results.append(('server_status', fetch_statuses(codes)))
            threading.Thread(target=worker, daemon=True).start()

        def periodic_servers(self):
            if self.closed:
                return
            self.sync_servers()
            self.after(300000, self.periodic_servers)

        def sync_servers(self):
            if self.closed or self.catalog_syncing:
                return
            self.catalog_syncing = True
            self.catalog_status.configure(text=tr('Sinkronisasi dari GitHub...'))

            def worker():
                try:
                    self.results.append(('catalog', sync_catalog(self.catalog_cache)))
                except Exception as exc:
                    self.results.append(('catalog_error', str(exc)))
            threading.Thread(target=worker, daemon=True).start()

        def connect_server(self, code):
            try:
                uri = connect_uri(code)
                if os.name != 'nt':
                    raise OSError('FiveM connection requires Windows')
                os.startfile(uri)
                self.feedback.configure(text=tr('Menghubungkan ke ') + code)
            except OSError:
                messagebox.showerror(tr('Koneksi server'), tr('FiveM belum terdaftar sebagai pembuka tautan. Jalankan FiveM sekali, lalu coba lagi.'), parent=self)

        def art(self, parent, name, background):
            scale = ctk.ScalingTracker.get_widget_scaling(self)
            suffix = '1' if scale <= 1.1 else '125' if scale <= 1.35 else '150' if scale <= 1.7 else '2'
            key = name + '_' + suffix
            if key not in self.images:
                self.images[key] = PhotoImage(master=self, file=os.path.join(assets, 'ui', key + '.png'))
            return Label(parent, image=self.images[key], bg=background, bd=0, highlightthickness=0)

        def open_link(self, url):
            import webbrowser
            try:
                if not webbrowser.open(url):
                    raise RuntimeError(tr('Browser tidak dapat dibuka.\n') + url)
            except Exception as exc:
                messagebox.showerror(tr('Buka tautan'), str(exc), parent=self)

        def animated_art(self, parent, name, background, page):
            import math
            label = self.art(parent, name, background)
            scale = ctk.ScalingTracker.get_widget_scaling(self)
            suffix = '1' if scale <= 1.1 else '125' if scale <= 1.35 else '150' if scale <= 1.7 else '2'
            picture = self.images[name + '_' + suffix]
            label.destroy()
            width, height = (picture.width(), picture.height())
            canvas = Canvas(parent, width=width, height=height, bg=background, bd=0, highlightthickness=0)
            motes = [canvas.create_oval(0, 0, 2, 2, fill='#98733e', outline='') for _ in range(10)]
            artwork = canvas.create_image(width / 2, height / 2, image=picture)
            animate = True
            if os.name == 'nt':
                enabled = ctypes.c_int(1)
                if ctypes.windll.user32.SystemParametersInfoW(4162, 0, ctypes.byref(enabled), 0):
                    animate = bool(enabled.value)
            start = time.monotonic()

            def tick():
                if self.closed or not canvas.winfo_exists():
                    return
                visible = self.page == page and self.state() != 'iconic'
                if animate and visible:
                    elapsed = time.monotonic() - start
                    canvas.coords(artwork, width / 2, height / 2 + math.sin(elapsed * 1.3) * 2 * scale)
                    for index, mote in enumerate(motes):
                        x = (index * 47 + math.sin(elapsed * 0.5 + index) * 10) % max(1, width - 12) + 6
                        y = height - (elapsed * 12 * scale + index * 29) % max(1, height - 12) - 6
                        radius = (1 + index % 2) * scale
                        canvas.coords(mote, x - radius, y - radius, x + radius, y + radius)
                    self.after(50, tick)
                elif animate:
                    self.after(250, tick)
                else:
                    for mote in motes:
                        canvas.itemconfigure(mote, state='hidden')
            self.after(50, tick)
            return canvas

        def btn(self, parent, text, command, primary=False, width=150, height=38):

            def guarded():
                if not self.busy:
                    command()
            b = ctk.CTkButton(parent, text=text, command=guarded, width=width, height=height, fg_color=RED if primary else '#f1e3cc', hover_color='#cf3444' if primary else '#e6d0aa', text_color='#ffffff' if primary else WHITE, border_color=RED if primary else LINE, border_width=1, corner_radius=6, font=(FONT, 12))
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
                b.configure(fg_color='#ead3b2' if key == name else 'transparent', text_color=GOLD if key == name else WHITE)

        def build_cache(self, page):
            page.grid_columnconfigure(0, weight=1)
            page.grid_rowconfigure(3, weight=1)
            ctk.CTkLabel(page, text=tr('Profil kota'), font=(FONT, 24, 'bold'), text_color=WHITE).grid(row=0, column=0, sticky='w', pady=(0, 18))
            summary = ctk.CTkFrame(page, fg_color=CARD, border_color=LINE, border_width=1, corner_radius=14)
            summary.grid(row=1, column=0, sticky='ew', pady=(0, 16))
            summary.grid_columnconfigure(1, weight=1)
            self.art(summary, 'status', CARD).grid(row=0, column=0, padx=(12, 4), pady=10)
            text = ctk.CTkFrame(summary, fg_color='transparent')
            text.grid(row=0, column=1, sticky='ew', padx=8, pady=14)
            ctk.CTkLabel(text, text=tr('CACHE AKTIF'), text_color=MUTED, font=(FONT, 10, 'bold'), anchor='w').pack(fill='x')
            self.status = ctk.CTkLabel(text, text='', font=(FONT, 19, 'bold'), text_color=GOLD, anchor='w', wraplength=365, justify='left')
            self.status.pack(fill='x', pady=(3, 0))
            self.connection = ctk.CTkLabel(text, text='', text_color=MUTED, font=(FONT, 10), anchor='w')
            self.connection.pack(fill='x')
            stats = ctk.CTkFrame(summary, fg_color='transparent')
            stats.grid(row=0, column=2, padx=20, pady=15)
            self.metric_count = ctk.CTkLabel(stats, text=tr('0 PROFIL'), text_color=WHITE, font=(FONT, 13, 'bold'))
            self.metric_count.pack(anchor='e')
            self.metric_size = ctk.CTkLabel(stats, text=tr('0 B tersimpan'), text_color=MUTED, font=(FONT, 10))
            self.metric_size.pack(anchor='e', pady=(4, 0))
            row = ctk.CTkFrame(page, fg_color='transparent')
            row.grid(row=2, column=0, sticky='ew', pady=(0, 10))
            self.count = ctk.CTkLabel(row, text=tr('PROFIL KOTA'), font=(FONT, 14, 'bold'), text_color=WHITE)
            self.count.pack(side='left')
            self.btn(row, tr('+ Tambah kota'), self.add, primary=True, width=142).pack(side='right')
            self.btn(row, 'Refresh', self.refresh, width=90).pack(side='right', padx=8)
            self.list = ctk.CTkScrollableFrame(page, fg_color='transparent', corner_radius=0, scrollbar_button_color='#c2a474', scrollbar_button_hover_color=RED)
            self.list.grid(row=3, column=0, sticky='nsew')
            self.path_label = ctk.CTkLabel(page, text='', anchor='w', text_color=MUTED, font=(FONT, 10), wraplength=780, justify='left')
            self.path_label.grid(row=4, column=0, sticky='ew', pady=(9, 0))
            ctk.CTkLabel(page, text=tr('Tutup FiveM sebelum switch. Cache kota disimpan secara terpisah.'), anchor='w', text_color='#786757', font=(FONT, 10)).grid(row=5, column=0, sticky='ew', pady=(2, 0))

        def build_tools(self, page):
            page.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(page, text=tr('PERALATAN'), font=(FONT, 24, 'bold'), text_color=WHITE).grid(row=0, column=0, sticky='w', pady=(0, 4))
            ctk.CTkLabel(page, text=tr('Kontrol instalasi, file sementara, dan jaringanmu.'), text_color=MUTED, font=(FONT, 12)).grid(row=1, column=0, sticky='w', pady=(0, 22))
            card = ctk.CTkFrame(page, fg_color=CARD, border_width=1, border_color=LINE, corner_radius=8)
            card.grid(row=2, column=0, sticky='ew', pady=(0, 14))
            ctk.CTkLabel(card, text=tr('INSTALASI & PEMULIHAN'), font=(FONT, 14, 'bold'), text_color=GOLD).pack(anchor='w', padx=20, pady=(18, 8))
            ctk.CTkLabel(card, text=tr('Buka lokasi cache atau pulihkan switch yang belum selesai.'), text_color=MUTED, font=(FONT, 11)).pack(anchor='w', padx=20)
            actions = ctk.CTkFrame(card, fg_color='transparent')
            actions.pack(fill='x', padx=20, pady=(12, 18))
            self.btn(actions, tr('Buka folder data'), self.open_folder).pack(side='left')
            self.btn(actions, tr('Pulihkan Switch'), self.recover).pack(side='left', padx=10)
            self.btn(actions, tr('Pilih FiveM.exe'), self.change_path, primary=True).pack(side='right')
            self.exe_label = ctk.CTkLabel(card, text='', text_color=MUTED, font=(FONT, 10), wraplength=700, justify='left', anchor='w')
            self.exe_label.pack(fill='x', padx=20, pady=(0, 14))
            temp = ctk.CTkFrame(page, fg_color=CARD, border_width=1, border_color=LINE, corner_radius=8)
            temp.grid(row=3, column=0, sticky='ew', pady=(0, 14))
            ctk.CTkLabel(temp, text='WINDOWS TEMP CLEANER', text_color=GOLD, font=(FONT, 14, 'bold')).pack(anchor='w', padx=20, pady=(18, 7))
            ctk.CTkLabel(temp, text=tr('Bersihkan file sementara. File terkunci akan dilewati.'), text_color=MUTED, font=(FONT, 11)).pack(anchor='w', padx=20)
            temp_row = ctk.CTkFrame(temp, fg_color='transparent')
            temp_row.pack(fill='x', padx=20, pady=(12, 18))
            self.temp_choice = ctk.CTkOptionMenu(temp_row, values=['User Temp', 'System Temp', tr('Semua Temp')], fg_color='#f1e3cc', button_color='#b82736', button_hover_color=RED, text_color=WHITE, width=210, font=(FONT, 12))
            self.temp_choice.pack(side='left')
            self.btn(temp_row, tr('Bersihkan'), self.clean, width=140).pack(side='right')
            dns = ctk.CTkFrame(page, fg_color=CARD, border_width=1, border_color=LINE, corner_radius=8)
            dns.grid(row=4, column=0, sticky='ew', pady=(0, 14))
            ctk.CTkLabel(dns, text='NETWORK DNS', text_color=GOLD, font=(FONT, 14, 'bold')).pack(anchor='w', padx=20, pady=(18, 7))
            ctk.CTkLabel(dns, text=tr('Pilih adapter. Pengaturan DNS memerlukan administrator.'), text_color=MUTED, font=(FONT, 11)).pack(anchor='w', padx=20)
            dr = ctk.CTkFrame(dns, fg_color='transparent')
            dr.pack(fill='x', padx=20, pady=(12, 18))
            self.adapter = ctk.CTkOptionMenu(dr, values=[tr('Pilih adapter')], width=230, fg_color='#f1e3cc', button_color='#b82736', button_hover_color=RED, text_color=WHITE, font=(FONT, 12))
            self.adapter.pack(side='left')
            self.dns_choice = ctk.CTkOptionMenu(dr, values=['Default (ISP)', 'Cloudflare', 'Google'], width=165, fg_color='#f1e3cc', button_color='#b82736', button_hover_color=RED, text_color=WHITE, font=(FONT, 12))
            self.dns_choice.pack(side='left', padx=12)
            self.btn(dr, tr('Terapkan DNS'), self.dns, primary=True, width=140).pack(side='right')
            language_card = ctk.CTkFrame(page, fg_color=CARD, border_width=1, border_color=LINE, corner_radius=8)
            language_card.grid(row=5, column=0, sticky='ew', pady=(0, 14))
            ctk.CTkLabel(language_card, text=tr('BAHASA APLIKASI'), text_color=GOLD, font=(FONT, 14, 'bold')).pack(anchor='w', padx=20, pady=(14, 8))
            language = ctk.CTkSegmentedButton(language_card, values=['Indonesia', 'English'], command=self.change_language, selected_color='#ead0b0', selected_hover_color='#e3c292', unselected_color='#fffaf1', text_color=WHITE, text_color_disabled=MUTED, height=28)
            language.set('English' if i18n.LANGUAGE == 'en' else 'Indonesia')
            language.pack(anchor='w', padx=20, pady=(0, 14))
            self.language_selector = language
            updates = ctk.CTkFrame(page, fg_color=CARD, corner_radius=8)
            updates.grid(row=6, column=0, sticky='ew', pady=(0, 14))
            self.btn(updates, tr('Cek update'), lambda: self.check_updates(manual=True), width=170).pack(side='right', padx=16, pady=16)
            self.update_status = ctk.CTkLabel(updates, text='v' + VERSION, text_color=MUTED, font=(FONT, 11), wraplength=430, justify='left')
            self.update_status.pack(side='left', padx=20, pady=16)


        def poll(self):
            while self.results:
                kind, value = self.results.pop(0)
                if kind == 'server_status':
                    self.status_syncing = False
                    self.server_statuses = value
                    self.render_servers()
                elif kind == 'catalog':
                    self.catalog_syncing = False
                    self.catalog = value
                    self.render_servers()
                    self.refresh_server_status()
                    self.catalog_status.configure(text=tr('Daftar tersinkron dari GitHub.'))
                elif kind == 'catalog_error':
                    self.catalog_syncing = False
                    self.catalog_status.configure(text=tr('Sync gagal; daftar terakhir tetap tersedia.'))
                elif kind == 'update_progress':
                    self.set_update_status(f"{tr('Mengunduh update: ')}{value:.0%}")
                    self.global_update_progress.grid()
                    self.global_update_progress.set(value)
                    self.global_update_button.grid_remove()
                    if hasattr(self, 'download_progress') and self.download_progress.winfo_exists():
                        self.download_progress.set(value)
                        self.download_label.configure(text=f"{tr('Mengunduh update... ')}{value:.0%}")
                elif kind == 'update_downloaded':
                    from auto_updater import start_replacement
                    try:
                        start_replacement(value, sys.executable, os.getpid(), os.getppid())
                    except Exception as exc:
                        import shutil
                        shutil.rmtree(os.path.dirname(value), ignore_errors=True)
                        self.finish_update_error(str(exc))
                    else:
                        self.closed = True
                        self.destroy()
                        return
                elif kind == 'update_failed':
                    self.finish_update_error(value)
                elif kind == 'update':
                    manual, release, error = value
                    self.update_checking = False
                    if error:
                        self.set_update_status(tr('Tidak dapat mengecek update.'))
                        if manual:
                            self.show_update_notice(error=error)
                    elif release:
                        self.latest_release = release
                        self.global_update_button.grid()
                        self.set_update_status(tr('Update tersedia: v') + release['version'])
                        self.show_update(release)
                    else:
                        self.set_update_status(tr('Belum ada versi yang lebih baru.'))
                        if manual:
                            self.show_update_notice()
                elif kind == 'sizes':
                    generation, sizes = value
                    if generation == self.size_generation and (not self.busy):
                        self.raw_sizes = sizes
                        self.sizes = {p: format_size(n) if n is not None else tr('Backup tidak ditemukan') for p, n in sizes.items()}
                        self.render()
                elif kind == 'adapters':
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
                            b.configure(state='normal')
                    if kind == 'error':
                        self.feedback.configure(text=tr('Operasi gagal. Lihat pesan untuk detail.'))
                        messagebox.showerror(tr('Operasi gagal'), str(value), parent=self)
                    else:
                        self.feedback.configure(text=str(value))
                    self.refresh()
            if not self.closed:
                self.after(100, self.poll)

        def set_update_status(self, text):
            self.update_status.configure(text=text)
            self.global_update_label.configure(text=text)
            self.update_banner.grid()
            if not self.latest_release or self.update_installing:
                self.global_update_button.grid_remove()

        def check_updates(self, manual=False):
            if self.closed or self.update_checking or self.update_installing:
                return
            self.update_checking = True
            self.set_update_status(tr('Mengecek update...'))

            def worker():
                try:
                    result = (manual, check_latest_release(), None)
                except Exception as e:
                    result = (manual, None, str(e))
                self.results.append(('update', result))
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
            dialog.title(tr('Pembaruan | ') + APP_NAME)
            dialog.configure(fg_color=BG)
            dialog.resizable(False, False)
            dialog.transient(self)
            # Keep a normal owned window so Windows can reliably bring it forward.
            scale = ctk.ScalingTracker.get_window_scaling(dialog)
            x = self.winfo_rootx() + (self.winfo_width() - round(540 * scale)) // 2
            y = self.winfo_rooty() + (self.winfo_height() - round(540 * scale)) // 2
            dialog.geometry(f'540x540+{max(0, x)}+{max(0, y)}')

            def close(event=None):
                if self.update_installing:
                    return
                if dialog.winfo_exists():
                    if dialog.grab_current() == dialog:
                        dialog.grab_release()
                    dialog.destroy()
                self.update_dialog = None
            dialog.protocol('WM_DELETE_WINDOW', close)
            dialog.bind('<Escape>', close)
            shell = ctk.CTkFrame(dialog, fg_color=CARD, border_color='#79523c', border_width=1, corner_radius=0)
            shell.pack(fill='both', expand=True)
            header = ctk.CTkFrame(shell, fg_color='#efdfc5', height=48, corner_radius=0)
            header.pack(fill='x', padx=1, pady=(1, 0))
            header.pack_propagate(False)
            brand = ctk.CTkLabel(header, text=tr('GANOMABI  /  PEMBARUAN'), text_color=GOLD, font=(FONT, 11, 'bold'))
            brand.pack(side='left', padx=22)
            ctk.CTkButton(header, text='×', width=36, height=30, corner_radius=6, fg_color='transparent', hover_color=RED, text_color=MUTED, font=(FONT, 22), command=close).pack(side='right', padx=10)
            drag = {}

            def start_drag(event):
                drag.update(x=event.x_root - dialog.winfo_x(), y=event.y_root - dialog.winfo_y())

            def move_drag(event):
                if drag:
                    dialog.geometry(f"+{max(0, event.x_root - drag['x'])}+{max(0, event.y_root - drag['y'])}")
            for widget in (header, brand):
                widget.bind('<ButtonPress-1>', start_drag)
                widget.bind('<B1-Motion>', move_drag)
            ctk.CTkFrame(shell, height=2, fg_color=RED, corner_radius=0).pack(fill='x', padx=1)
            head = ctk.CTkFrame(shell, fg_color='transparent')
            head.pack(fill='x', padx=26, pady=(18, 10))
            self.art(head, 'status', CARD).pack(side='left', padx=(0, 16))
            titles = ctk.CTkFrame(head, fg_color='transparent')
            titles.pack(side='left', fill='x', expand=True)
            title = tr('Update tersedia') if release else tr('Cek update gagal') if error else tr('Versi kamu sudah terbaru')
            subtitle = tr('Unduh dan pasang langsung dari aplikasi.') if release else tr('Coba lagi saat koneksi tersedia.') if error else tr('Belum ada rilis stabil yang lebih baru.')
            ctk.CTkLabel(titles, text=title, anchor='w', text_color=WHITE, font=(FONT, 20, 'bold')).pack(fill='x')
            ctk.CTkLabel(titles, text=subtitle, anchor='w', text_color=MUTED, font=(FONT, 11)).pack(fill='x', pady=(4, 0))
            versions = ctk.CTkFrame(shell, fg_color='#f5ead6', border_color=LINE, border_width=1, corner_radius=10)
            versions.pack(fill='x', padx=26, pady=(0, 14))

            def version_cell(parent, label, value, color):
                cell = ctk.CTkFrame(parent, fg_color='transparent')
                cell.pack(side='left', fill='x', expand=True, padx=18, pady=12)
                ctk.CTkLabel(cell, text=label, text_color=MUTED, font=(FONT, 10), anchor='w').pack(fill='x')
                ctk.CTkLabel(cell, text=value, text_color=color, font=(FONT, 20, 'bold'), anchor='w').pack(fill='x')
            version_cell(versions, tr('VERSI TERPASANG'), 'v' + VERSION, WHITE)
            version_cell(versions, tr('VERSI BARU') if release else 'STATUS', 'v' + release['version'] if release else 'Offline' if error else tr('Terkini'), GOLD)
            if release:
                description = tr('Update diunduh langsung, lalu aplikasi akan ditutup dan dibuka kembali. EXE lama diganti di lokasi yang sama. Pengaturan tetap tersimpan.')
            elif error:
                description = tr('Update belum dapat diselesaikan. ') + str(error)[:200]
            else:
                description = tr('Kamu bisa melanjutkan menggunakan aplikasi. Kami akan memberi notifikasi ketika rilis baru tersedia di GitHub.')
            ctk.CTkLabel(shell, text=description, text_color=MUTED, font=(FONT, 12), justify='left', anchor='w', wraplength=480).pack(fill='x', padx=28, pady=(0, 10))
            ctk.CTkLabel(shell, text='© 2026 GANOMABI / amiinarii', text_color='#786757', font=(FONT, 10)).pack(side='bottom', pady=(0, 14))
            row = ctk.CTkFrame(shell, fg_color='transparent')
            row.pack(side='bottom', fill='x', padx=26, pady=(6, 12))
            self.download_label = ctk.CTkLabel(shell, text='', text_color=GOLD, font=(FONT, 11))
            self.download_label.pack(fill='x', padx=28)
            self.download_progress = ctk.CTkProgressBar(shell, progress_color=RED, fg_color=LINE, height=5)
            self.download_progress.set(0)
            self.download_progress.pack(fill='x', padx=28, pady=4)

            def download():
                if self.update_installing:
                    return
                if os.name != 'nt' or not getattr(sys, 'frozen', False):
                    close()
                    self.show_update_notice(error=tr('Gunakan EXE Windows untuk memasang update otomatis.'))
                    return
                self.update_installing = True
                self.set_update_status(tr('Menyiapkan unduhan...'))
                self.global_update_progress.grid()
                self.global_update_button.grid_remove()
                primary.configure(state='disabled', text=tr('Mengunduh...'))
                self.download_label.configure(text=tr('Menyiapkan unduhan...'))

                def worker():
                    from auto_updater import download_update
                    try:
                        path = download_update(release, os.path.dirname(user_config_path()), lambda value: self.results.append(('update_progress', value)))
                        self.results.append(('update_downloaded', path))
                    except Exception as exc:
                        self.results.append(('update_failed', str(exc)))
                threading.Thread(target=worker, daemon=True).start()

            def retry():
                close()
                self.check_updates(manual=True)
            action = download if release else retry if error else close
            label = tr('Update sekarang') if release else tr('Coba lagi') if error else tr('Mengerti')
            primary = ctk.CTkButton(row, text=label, command=action, width=180, height=42, fg_color=RED, hover_color='#d13747', text_color='#ffffff', corner_radius=6, font=(FONT, 12))
            primary.pack(side='right')
            if release or error:
                ctk.CTkButton(row, text=tr('Nanti') if release else tr('Tutup'), command=close, width=120, height=42, fg_color='#f1e3cc', hover_color='#e6d0aa', text_color=WHITE, border_color=LINE, border_width=1, corner_radius=6, font=(FONT, 12)).pack(side='right', padx=(0, 10))
            dialog.bind('<Return>', lambda event: action())
            def present():
                if not dialog.winfo_exists():
                    return
                dialog.deiconify()
                dialog.lift()
                dialog.attributes('-topmost', True)
                dialog.grab_set()
                primary.focus_set()
                def release_topmost():
                    if dialog.winfo_exists():
                        dialog.attributes('-topmost', False)
                dialog.after(500, release_topmost)
            # CustomTkinter updates the Windows titlebar asynchronously; present
            # after that initialization so its withdraw/restore cannot hide us.
            dialog.after(250, present)

        def finish_update_error(self, error):
            self.update_installing = False
            self.global_update_progress.grid_remove()
            if self.latest_release:
                self.global_update_button.grid()
            self.set_update_status(tr('Update gagal. EXE lama tetap tersedia.'))
            if self.update_dialog is not None and self.update_dialog.winfo_exists():
                self.update_dialog.grab_release()
                self.update_dialog.destroy()
            self.update_dialog = None
            self.show_update_notice(error=error)

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
                    b.configure(state='disabled')

            def worker():
                try:
                    self.results.append(('done', work() or 'Selesai.'))
                except Exception as e:
                    self.results.append(('error', str(e)))
            threading.Thread(target=worker, daemon=True).start()

        def render(self):
            for w in self.list.winfo_children():
                w.destroy()
            self.buttons = [b for b in self.buttons if b.winfo_exists()]
            active = self.store.detect()
            labels = {None: tr('Belum ada cache aktif'), 'external': tr('Cache lama belum terdaftar'), 'conflict': tr('Backup perlu diperiksa')}
            self.status.configure(text=self.store.profiles.get(active, labels.get(active, tr('Belum diketahui'))), text_color=GOLD)
            if os.path.isfile(self.store.journal):
                self.status.configure(text=tr('Switch perlu dipulihkan'))
            linked = bool(self.store.exe and os.path.isfile(self.store.exe) and os.path.isdir(self.store.data_dir))
            self.connection.configure(text=tr('Instalasi terhubung') if linked else tr('Pilih FiveM.exe untuk mulai'))
            self.metric_count.configure(text=f"{len(self.store.profiles)}{tr(' PROFIL')}")
            total = sum((n for n in self.raw_sizes.values() if n is not None))
            self.metric_size.configure(text=format_size(total) + tr(' tersimpan'))
            self.count.configure(text=f"{tr('PROFIL KOTA  /  ')}{len(self.store.profiles):02d}")
            if not self.store.profiles:
                empty = ctk.CTkFrame(self.list, fg_color=CARD, border_color=LINE, border_width=1, corner_radius=14)
                empty.pack(fill='x', pady=6)
                self.art(empty, 'empty', CARD).pack(pady=(18, 3))
                ctk.CTkLabel(empty, text=tr('Perjalanan baru dimulai di sini.'), text_color=WHITE, font=(FONT, 16, 'bold')).pack()
                ctk.CTkLabel(empty, text=tr('Pilih FiveM.exe, lalu tambahkan kota pertamamu.'), text_color=MUTED, font=(FONT, 11)).pack(pady=(5, 20))
            for index, (pid, name) in enumerate(self.store.profiles.items()):
                current = active == pid
                bg = '#fae6d1' if current else CARD
                card = ctk.CTkFrame(self.list, fg_color=bg, border_color='#b68b48' if current else LINE, border_width=1, corner_radius=12)
                card.pack(fill='x', pady=(0, 9))
                badge = ctk.CTkFrame(card, fg_color='#ead0b0' if current else '#efe0c7', width=46, height=46, corner_radius=12)
                badge.pack(side='left', padx=(16, 10), pady=15)
                badge.pack_propagate(False)
                ctk.CTkLabel(badge, text=f'{index + 1:02d}', font=(FONT, 16, 'bold'), text_color=GOLD).pack(expand=True)
                info = ctk.CTkFrame(card, fg_color='transparent')
                info.pack(side='left', fill='x', expand=True, padx=(0, 8), pady=13)
                short = name if len(name) <= 30 else name[:27] + '...'
                ctk.CTkLabel(info, text=short, anchor='w', font=(FONT, 15, 'bold'), text_color=WHITE).pack(fill='x')
                ctk.CTkLabel(info, text=(tr('AKTIF  /  ') if current else tr('TERSIMPAN  /  ')) + self.sizes.get(pid, tr('Menghitung...')), anchor='w', text_color=GOLD if current else MUTED, font=(FONT, 10)).pack(fill='x', pady=(2, 0))
                actions = ctk.CTkFrame(card, fg_color='transparent')
                actions.pack(side='right', padx=13)
                switch = self.btn(actions, tr('Sedang aktif') if current else tr('Aktifkan'), lambda p=pid: self.switch(p), primary=not current, width=106, height=35)
                switch.pack(side='left', padx=(0, 8))
                if current:
                    switch.configure(state='disabled', text_color_disabled=GOLD)
                self.btn(actions, tr('Nama'), lambda p=pid: self.rename(p), width=56, height=35).pack(side='left', padx=(0, 5))
                self.btn(actions, tr('Hapus'), lambda p=pid: self.delete(p), width=56, height=35).pack(side='left')
            if self.busy:
                for b in self.buttons:
                    if b.winfo_exists():
                        b.configure(state='disabled')

        def refresh(self):
            if self.busy:
                return
            self.exe_label.configure(text=self.store.exe or tr('FiveM.exe belum dipilih'))
            self.path_label.configure(text='CACHE  /  ' + self.store.active if self.store.exe else tr('CACHE  /  menunggu lokasi FiveM.exe'))
            self.size_generation += 1
            generation = self.size_generation
            active = self.store.detect()
            paths = {p: self.store.active if p == active else self.store.backup(p) for p in self.store.profiles}
            self.sizes, self.raw_sizes = ({}, {})
            self.render()

            def worker():
                sizes = {p: folder_size(path) if os.path.isdir(path) else None for p, path in paths.items()}
                self.results.append(('sizes', (generation, sizes)))
            threading.Thread(target=worker, daemon=True).start()

        def add(self):
            try:
                self.store.validate()
            except Exception as e:
                messagebox.showinfo(tr('Hubungkan FiveM'), str(e), parent=self)
                self.change_path()
                return
            name = self.ask_profile(tr('Tambah kota / cache'), tr('Nama kota atau profil cache'), confirm=tr('Tambah kota'))
            if name and name.strip():
                self.run(tr('Membuat profil...'), lambda: (self.store.add(name.strip()), tr('Profil dibuat.'))[1])

        def rename(self, pid):
            name = self.ask_profile(tr('Ubah nama profil'), tr('Nama kota atau profil cache'), initial=self.store.profiles[pid], confirm=tr('Simpan nama'))
            if name and name.strip():
                self.run(tr('Menyimpan nama...'), lambda: (self.store.rename(pid, name.strip()), tr('Nama diperbarui.'))[1])

        def ask_profile(self, title, prompt, initial='', confirm='Simpan'):
            dialog = ctk.CTkToplevel(self)
            dialog.withdraw()
            dialog.title(title + ' | ' + APP_NAME)
            dialog.configure(fg_color=BG)
            dialog.resizable(False, False)
            dialog.transient(self)
            dialog.result = None
            try:
                dialog.iconbitmap(os.path.join(assets, 'ganomabi.ico'))
            except Exception:
                pass
            scale = ctk.ScalingTracker.get_window_scaling(dialog)
            x = self.winfo_rootx() + (self.winfo_width() - round(520 * scale)) // 2
            y = self.winfo_rooty() + (self.winfo_height() - round(360 * scale)) // 2
            dialog.geometry(f'520x360+{max(0, x)}+{max(0, y)}')
            card = ctk.CTkFrame(dialog, fg_color=CARD, border_color=LINE, border_width=1, corner_radius=14)
            card.pack(fill='both', expand=True, padx=12, pady=12)
            head = ctk.CTkFrame(card, fg_color='transparent')
            head.pack(fill='x', padx=20, pady=(10, 2))
            self.art(head, 'status', CARD).pack(side='left', padx=(0, 12))
            titles = ctk.CTkFrame(head, fg_color='transparent')
            titles.pack(side='left', fill='x', expand=True)
            ctk.CTkLabel(titles, text=APP_NAME, text_color=GOLD, font=(FONT, 10, 'bold'), anchor='w').pack(fill='x')
            ctk.CTkLabel(titles, text=title, text_color=WHITE, font=(FONT, 20, 'bold'), anchor='w').pack(fill='x', pady=4)
            ctk.CTkLabel(card, text=prompt, text_color=MUTED, font=(FONT, 12), anchor='w').pack(fill='x', padx=24, pady=(8, 5))
            entry = ctk.CTkEntry(card, height=44, fg_color='#f5ead6', border_color='#8e6846', border_width=1, corner_radius=9, text_color=WHITE, placeholder_text=tr('Contoh: GANOMABI City'), placeholder_text_color='#786757', font=(FONT, 14))
            entry.pack(fill='x', padx=24)
            if initial:
                entry.insert(0, initial)
            hint = ctk.CTkLabel(card, text=tr('Setiap kota memiliki cache yang terpisah.'), text_color=MUTED, font=(FONT, 11), anchor='w')
            hint.pack(fill='x', padx=24, pady=(7, 10))
            buttons = ctk.CTkFrame(card, fg_color='transparent')
            buttons.pack(fill='x', padx=24, pady=(0, 18))

            def submit(event=None):
                name = entry.get().strip()
                if not name:
                    hint.configure(text=tr('Isi nama kota terlebih dahulu.'), text_color='#ee7782')
                    entry.focus_set()
                    return
                dialog.result = name
                dialog.destroy()
            self.btn(buttons, confirm, submit, primary=True, width=158, height=40).pack(side='right')
            self.btn(buttons, tr('Batal'), dialog.destroy, width=110, height=40).pack(side='right', padx=9)
            dialog.bind('<Return>', submit)
            dialog.bind('<Escape>', lambda e: dialog.destroy())
            dialog.deiconify()
            dialog.wait_visibility()
            dialog.grab_set()
            dialog.after(80, lambda: (entry.focus_set(), entry.select_range(0, 'end')) if initial else entry.focus_set())
            self.wait_window(dialog)
            return dialog.result

        def switch(self, pid):
            name = self.store.profiles[pid]
            self.run(tr('Mengaktifkan ') + name + '...', lambda: (self.store.switch(pid), tr('Cache aktif: ') + name)[1])

        def delete(self, pid):
            if messagebox.askyesno(tr('Hapus profil'), tr("Hapus profil '") + self.store.profiles[pid] + tr("'?\n\nCache dipindahkan ke cache-switcher-trash dan bisa dipulihkan manual."), parent=self):
                self.run(tr('Memindahkan cache...'), lambda: tr('Cache disimpan di: ') + self.store.delete(pid))

        def change_path(self):
            exe = filedialog.askopenfilename(title=tr('Pilih FiveM.exe'), initialdir=os.path.dirname(self.store.exe) if self.store.exe else os.path.expanduser('~'), filetypes=[('FiveM Launcher', 'FiveM.exe'), ('Executable', '*.exe')], parent=self)
            if not exe:
                return
            try:
                no_fivem()
                locations = find_data_directories(exe)
                if len(locations) == 1:
                    data = locations[0]
                else:
                    messagebox.showinfo(tr('Pilih lokasi data'), tr('Ada beberapa lokasi data atau folder data belum terdeteksi.\nPilih folder data yang berisi server-cache-priv milik FiveM ini.'), parent=self)
                    data = filedialog.askdirectory(title=tr('Pilih folder data milik FiveM ini'), initialdir=os.path.dirname(exe), parent=self)
                    if not data:
                        return
                if self.store.profiles and os.path.normcase(os.path.dirname(os.path.abspath(data))) != os.path.normcase(os.path.abspath(self.store.path)) and (not messagebox.askyesno(tr('Ganti instalasi'), tr('Tampilkan profil milik instalasi yang baru?\nCache instalasi sebelumnya tetap tersedia di folder asal.'), parent=self)):
                    return
                self.run(tr('Menghubungkan FiveM.exe...'), lambda: (self.store.select_exe(exe, data), tr('FiveM terhubung. Backup kota yang ditemukan ditampilkan.'))[1])
            except Exception as e:
                messagebox.showerror(tr('Lokasi FiveM'), str(e), parent=self)

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
                    messagebox.showerror(tr('Launch gagal'), str(e), parent=self)
            else:
                self.change_path()

        def recover(self):
            if not os.path.isfile(self.store.journal):
                messagebox.showinfo(tr('Pemulihan'), tr('Tidak ada switch yang perlu dipulihkan.'), parent=self)
                return
            self.run(tr('Memulihkan switch...'), lambda: (self.store.recover(), tr('Cache sebelumnya dipulihkan.'))[1])

        def clean(self):
            choice = self.temp_choice.get()
            user = os.environ.get('TEMP', '')
            system = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'Temp')
            paths = [user] if choice == 'User Temp' else [system] if choice == 'System Temp' else [user, system]
            if messagebox.askyesno(tr('Bersihkan Temp'), tr('Hapus isi folder berikut?\n\n') + '\n'.join(paths) + tr('\n\nFile yang dipakai atau terkunci akan dilewati.'), parent=self):

                def work():
                    removed, skipped = clean_temp(paths)
                    return f"Temp: {removed}{tr(' item dibersihkan, ')}{skipped}{tr(' dilewati.')}"
                self.run(tr('Membersihkan Temp...'), work)

        def load_adapters(self):

            def worker():
                try:
                    r = subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command', "Get-NetAdapter | Where-Object Status -eq 'Up' | Select-Object -ExpandProperty Name"], capture_output=True, text=True, creationflags=134217728, timeout=20)
                    if r.returncode == 0:
                        self.results.append(('adapters', [n.strip() for n in r.stdout.splitlines() if n.strip()]))
                except Exception:
                    pass
            threading.Thread(target=worker, daemon=True).start()

        def dns(self):
            adapter, choice = (self.adapter.get(), self.dns_choice.get())
            if adapter == tr('Pilih adapter'):
                messagebox.showinfo(tr('Adapter'), tr('Tidak ada adapter aktif yang terdeteksi.'), parent=self)
                self.load_adapters()
                return
            if messagebox.askyesno(tr('Ubah DNS'), f"""{tr('Terapkan ')}{choice}{tr(" pada adapter '")}{adapter}'?""", parent=self):
                self.run(tr('Mengatur DNS...'), lambda: (set_dns(adapter, choice), f"DNS {choice}{tr(' diterapkan ke ')}{adapter}.")[1])

        def close(self):
            if self.update_installing:
                return
            if self.busy:
                messagebox.showinfo(tr('Sedang bekerja'), tr('Tunggu operasi selesai sebelum menutup aplikasi.'), parent=self)
                return
            self.closed = True
            self.destroy()
    mutex = None
    if os.name == 'nt':
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.CreateMutexW.restype = ctypes.c_void_p
        kernel.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p]
        mutex = kernel.CreateMutexW(None, False, 'Local\\FiveMCacheSwitcherRemake')
        if ctypes.get_last_error() == 183:
            messagebox.showinfo(APP_NAME, tr('Aplikasi sudah terbuka.'))
            return
    app = App()
    app.mainloop()
    if mutex:
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        kernel.CloseHandle(mutex)


if __name__ == "__main__":
    main()
