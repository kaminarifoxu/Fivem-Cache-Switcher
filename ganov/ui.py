"""Desktop interface and application startup."""

import ctypes
import os
import subprocess
import sys
import threading
import time
from .core import (
    APP_NAME,
    COPYRIGHT,
    GITHUB_REPOSITORY,
    VERSION,
    check_latest_release,
    clean_temp,
    find_data_directories,
    folder_size,
    format_size,
    no_fivem,
    open_user_store,
    set_dns,
    user_config_path,
)


def main():
    import customtkinter as ctk
    from tkinter import messagebox, filedialog, PhotoImage, Label, Canvas
    from . import i18n
    from .i18n import tr
    from .server_catalog import load_catalog, sync_catalog, connect_uri
    from .server_status import fetch_statuses, page_url
    from .server_icons import fetch_icons
    from .wallpaper import Wallpaper, WallpaperText
    from .ui_icons import make_icon

    ui_settings_path = os.path.join(
        os.path.dirname(user_config_path()), "ui_settings.json"
    )
    i18n.load(ui_settings_path)
    from . import app_theme

    theme_settings_path = os.path.join(
        os.path.dirname(user_config_path()), "theme.json"
    )
    app_theme.load(theme_settings_path)
    ctk.set_appearance_mode(app_theme.THEME)
    BG, CARD, LINE = (
        app_theme.color("#f7f0e3"),
        app_theme.color("#fffaf1"),
        app_theme.color("#ddc8a3"),
    )
    RED, GOLD, MUTED, WHITE = (
        app_theme.color("#b82736"),
        app_theme.color("#896019"),
        app_theme.color("#786757"),
        app_theme.color("#30251e"),
    )
    FONT = "Segoe UI" if os.name == "nt" else "DejaVu Sans"
    base = os.path.dirname(
        sys.executable
        if getattr(sys, "frozen", False)
        else os.path.dirname(os.path.abspath(__file__))
    )
    assets = os.path.join(getattr(sys, "_MEIPASS", base), "assets")

    def text_label(parent, **kwargs):
        current = parent
        while current is not None:
            layer = getattr(current, "_wallpaper_layer", None)
            if layer:
                return WallpaperText(parent, layer, **kwargs)
            try:
                if current.cget("fg_color") != "transparent":
                    break
            except Exception:
                break
            current = current.master
        return ctk.CTkLabel(parent, **kwargs)

    class App(ctk.CTk):

        def __init__(self):
            super().__init__()
            self.withdraw()
            self.title(APP_NAME)
            self.geometry("1220x880")
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
            self.page = "cache"
            self.ui_started = False
            self.page_animation = None
            self.page_animation_generation = 0
            self.animations_enabled = True
            if os.name == "nt":
                enabled = ctypes.c_int(1)
                if ctypes.windll.user32.SystemParametersInfoW(
                    4162, 0, ctypes.byref(enabled), 0
                ):
                    self.animations_enabled = bool(enabled.value)
            self.catalog_syncing = False
            self.server_statuses = {}
            self.server_icons = {}
            self.server_logo_images = []
            self.status_syncing = False
            self.server_page = 0
            self.catalog_cache = os.path.join(
                os.path.dirname(user_config_path()), "servers_cache.json"
            )
            self.catalog = load_catalog(
                self.catalog_cache,
                os.path.join(getattr(sys, "_MEIPASS", base), "servers.json"),
            )
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
            frame = ctk.CTkFrame(
                self.splash,
                fg_color=app_theme.color("#211219"),
                border_color=app_theme.color("#794336"),
                border_width=1,
                corner_radius=16,
            )
            frame.pack(fill="both", expand=True, padx=2, pady=2)
            self.art(frame, "sidebar", app_theme.color("#211219")).pack(pady=(16, 0))
            ctk.CTkLabel(
                frame, text=APP_NAME, text_color=GOLD, font=(FONT, 20, "bold")
            ).pack(pady=(8, 0))
            ctk.CTkLabel(
                frame,
                text="Cache Switch",
                text_color=MUTED,
                font=(FONT, 12),
            ).pack(pady=(0, 19))
            self.splash_progress = ctk.CTkProgressBar(
                frame, width=420, height=7, fg_color=LINE, progress_color=GOLD
            )
            self.splash_progress.pack()
            self.splash_progress.set(0.08)
            self.splash_status = ctk.CTkLabel(
                frame,
                text=tr("Menyiapkan aplikasi..."),
                text_color=MUTED,
                font=(FONT, 11),
            )
            self.splash_status.pack(pady=10)
            ctk.CTkLabel(frame, text=COPYRIGHT, text_color=MUTED, font=(FONT, 9)).pack(
                pady=(0, 3)
            )
            self.splash.deiconify()
            self.splash.lift()
            self.splash.attributes("-topmost", True)

        def initialize(self):
            try:
                self.splash_status.configure(
                    text=tr("Membaca konfigurasi dan lokasi FiveM...")
                )
                self.splash_progress.set(0.25)
                self.update_idletasks()
                self.store = open_user_store(base)
                self.splash_status.configure(
                    text=tr("Menyiapkan profil kota dan tampilan...")
                )
                self.splash_progress.set(0.55)
                self.update_idletasks()
                self.build_main_ui()
                self.splash_status.configure(
                    text=tr("Siap. Selamat datang di GANOMABI.")
                )
                self.splash_progress.set(1)
                self.after(220, self.finish_startup)
            except Exception as e:
                self.splash.destroy()
                messagebox.showerror(tr("Aplikasi gagal dibuka"), str(e), parent=self)
                self.closed = True
                self.destroy()

        def finish_startup(self):
            self.splash.destroy()
            self.splash = None
            self.deiconify()
            self.lift()
            if self.store.load_warning:
                messagebox.showwarning(
                    tr("Konfigurasi"), self.store.load_warning, parent=self
                )
            self.after(800, self.check_updates)

        def build_main_ui(self):
            self.wallpaper_layers = []

            def add_wallpaper(parent):
                try:
                    self.wallpaper_layers.append(
                        Wallpaper(
                            parent,
                            os.path.join(assets, "wallpaper.jpg"),
                            app_theme.THEME,
                        )
                    )
                except (OSError, ValueError):
                    pass

            self.add_wallpaper = add_wallpaper
            add_wallpaper(self)
            self.grid_columnconfigure(1, weight=1)
            self.grid_rowconfigure(0, weight=1)
            side = ctk.CTkFrame(
                self, width=220, fg_color=app_theme.color("#efe0c7"), corner_radius=0
            )
            side.grid_propagate(False)
            self.sidebar = side
            side.grid(row=0, column=0, sticky="nsew")
            add_wallpaper(side)
            from PIL import Image

            brand = WallpaperText(side, side._wallpaper_layer, width=100, height=64)
            with Image.open(os.path.join(assets, "ganomabi.ico")) as logo:
                brand.art_image = logo.convert("RGBA")
            brand.pack(pady=(20, 6))
            text_label(
                side, text="GanoV", text_color=GOLD, font=(FONT, 20, "bold")
            ).pack(pady=(0, 3))
            text_label(
                side,
                text="CACHE & STORAGE",
                text_color=MUTED,
                font=(FONT, 10),
            ).pack(pady=(0, 22))
            self.nav = {}
            for key, text in [
                ("cache", tr("Profil kota")),
                ("servers", tr("Daftar server")),
                ("tools", tr("Peralatan")),
            ]:
                self.nav[key] = self.btn(
                    side, text, lambda p=key: self.show_page(p), width=180
                )
                self.nav[key].pack(fill="x", padx=22, pady=4)
            ctk.CTkFrame(side, height=1, fg_color=LINE).pack(fill="x", padx=24, pady=21)
            self.btn(side, tr("Jalankan FiveM"), self.launch, primary=True).pack(
                fill="x", padx=22, pady=(0, 7)
            )
            links = ctk.CTkFrame(side, fg_color="transparent")
            links.pack(fill="x", padx=22, pady=(2, 6))
            self.btn(
                links,
                "GitHub",
                lambda: self.open_link("https://github.com/" + GITHUB_REPOSITORY),
                width=98,
                height=34,
            ).pack(side="left")
            self.btn(
                links,
                tr("Donasi"),
                lambda: self.open_link("https://saweria.co/itsaminarii"),
                primary=True,
  …13690 tokens truncated…_update_button.grid()
                        self.set_update_status(
                            tr("Update tersedia: v") + release["version"]
                        )
                        self.show_update(release)
                    else:
                        self.set_update_status(tr("Belum ada versi yang lebih baru."))
                        if manual:
                            self.show_update_notice()
                elif kind == "sizes":
                    generation, sizes = value
                    if generation == self.size_generation and (not self.busy):
                        self.raw_sizes = sizes
                        self.sizes = {
                            p: (
                                format_size(n)
                                if n is not None
                                else tr("Backup tidak ditemukan")
                            )
                            for p, n in sizes.items()
                        }
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
                        self.feedback.configure(
                            text=tr("Operasi gagal. Lihat pesan untuk detail.")
                        )
                        messagebox.showerror(
                            tr("Operasi gagal"), str(value), parent=self
                        )
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

        def open_update_panel(self):
            self.feedback.configure(text=tr("Membuka panel update..."))
            try:
                if self.latest_release:
                    self.show_update(self.latest_release)
                else:
                    self.check_updates(manual=True)
            except Exception as exc:
                self.feedback.configure(
                    text=tr("Update gagal. EXE lama tetap tersedia.")
                )
                messagebox.showerror(tr("Cek update gagal"), str(exc), parent=self)

        def manual_update_check(self):
            if self.update_dialog is not None and self.update_dialog.winfo_exists():
                self.show_update_notice(release=self.latest_release)
            elif self.update_checking:
                self.set_update_status(tr("Mengecek update..."))
            else:
                self.check_updates(manual=True)

        def check_updates(self, manual=False):
            if self.closed or self.update_checking or self.update_installing:
                return
            self.update_checking = True
            self.set_update_status(tr("Mengecek update..."))

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
            if self.update_dialog is not None and self.update_dialog.winfo_exists():
                self.update_dialog.place(relx=0.5, rely=0.5, anchor="center")
                self.update_dialog.lift()
                self.update_dialog.focus_force()
                return
            if self.busy or self.grab_current() is not None:
                self.after(500, lambda: self.show_update_notice(release, error))
                return
            dialog = self.update_dialog = ctk.CTkFrame(
                self,
                width=540,
                height=650,
                fg_color=CARD,
                border_width=1,
                border_color=LINE,
                corner_radius=12,
            )
            dialog.pack_propagate(False)
            dialog.place(relx=0.5, rely=0.5, anchor="center")
            dialog.lift()

            def close(event=None):
                if self.update_installing:
                    return
                if dialog.winfo_exists():
                    if dialog.grab_current() == dialog:
                        dialog.grab_release()
                    dialog.destroy()
                self.update_dialog = None

            dialog.bind("<Escape>", close)
            shell = ctk.CTkFrame(
                dialog,
                fg_color=CARD,
                border_color=app_theme.color("#79523c"),
                border_width=1,
                corner_radius=0,
            )
            shell.pack(fill="both", expand=True)
            header = ctk.CTkFrame(
                shell, fg_color=app_theme.color("#efdfc5"), height=48, corner_radius=0
            )
            header.pack(fill="x", padx=1, pady=(1, 0))
            header.pack_propagate(False)
            brand = ctk.CTkLabel(
                header,
                text=tr("GANOMABI  /  PEMBARUAN"),
                text_color=GOLD,
                font=(FONT, 11, "bold"),
            )
            brand.pack(side="left", padx=22)
            ctk.CTkButton(
                header,
                text="×",
                width=36,
                height=30,
                corner_radius=6,
                fg_color="transparent",
                hover_color=RED,
                text_color=MUTED,
                font=(FONT, 22),
                command=close,
            ).pack(side="right", padx=10)
            ctk.CTkFrame(shell, height=2, fg_color=RED, corner_radius=0).pack(
                fill="x", padx=1
            )
            head = ctk.CTkFrame(shell, fg_color="transparent")
            head.pack(fill="x", padx=26, pady=(18, 10))
            self.art(head, "status", CARD).pack(side="left", padx=(0, 16))
            titles = ctk.CTkFrame(head, fg_color="transparent")
            titles.pack(side="left", fill="x", expand=True)
            title = (
                tr("Update tersedia")
                if release
                else tr("Cek update gagal") if error else tr("Versi kamu sudah terbaru")
            )
            subtitle = (
                tr("Unduh dan pasang langsung dari aplikasi.")
                if release
                else (
                    tr("Coba lagi saat koneksi tersedia.")
                    if error
                    else tr("Belum ada rilis stabil yang lebih baru.")
                )
            )
            ctk.CTkLabel(
                titles,
                text=title,
                anchor="w",
                text_color=WHITE,
                font=(FONT, 20, "bold"),
            ).pack(fill="x")
            ctk.CTkLabel(
                titles, text=subtitle, anchor="w", text_color=MUTED, font=(FONT, 11)
            ).pack(fill="x", pady=(4, 0))
            versions = ctk.CTkFrame(
                shell,
                fg_color=app_theme.color("#f5ead6"),
                border_color=LINE,
                border_width=1,
                corner_radius=10,
            )
            versions.pack(fill="x", padx=26, pady=(0, 14))

            def version_cell(parent, label, value, color):
                cell = ctk.CTkFrame(parent, fg_color="transparent")
                cell.pack(side="left", fill="x", expand=True, padx=18, pady=12)
                ctk.CTkLabel(
                    cell, text=label, text_color=MUTED, font=(FONT, 10), anchor="w"
                ).pack(fill="x")
                ctk.CTkLabel(
                    cell,
                    text=value,
                    text_color=color,
                    font=(FONT, 20, "bold"),
                    anchor="w",
                ).pack(fill="x")

            version_cell(versions, tr("VERSI TERPASANG"), "v" + VERSION, WHITE)
            version_cell(
                versions,
                tr("VERSI BARU") if release else "STATUS",
                (
                    "v" + release["version"]
                    if release
                    else "Offline" if error else tr("Terkini")
                ),
                GOLD,
            )
            if release:
                description = tr(
                    "Update diunduh langsung, lalu aplikasi akan ditutup dan dibuka kembali. EXE lama diganti di lokasi yang sama. Pengaturan tetap tersimpan."
                )
            elif error:
                description = tr("Update belum dapat diselesaikan. ") + str(error)[:200]
            else:
                description = tr(
                    "Kamu bisa melanjutkan menggunakan aplikasi. Kami akan memberi notifikasi ketika rilis baru tersedia di GitHub."
                )
            ctk.CTkLabel(
                shell,
                text=description,
                text_color=MUTED,
                font=(FONT, 12),
                justify="left",
                anchor="w",
                wraplength=480,
            ).pack(fill="x", padx=28, pady=(0, 10))
            if release:
                ctk.CTkLabel(
                    shell,
                    text=tr("Yang baru"),
                    text_color=GOLD,
                    font=(FONT, 12, "bold"),
                    anchor="w",
                ).pack(fill="x", padx=28, pady=(0, 4))
                summary = release.get("summary") or tr(
                    "Ringkasan belum tersedia. Lihat catatan rilis di GitHub."
                )
                self.release_summary_label = ctk.CTkLabel(
                    shell,
                    text=summary,
                    text_color=WHITE,
                    font=(FONT, 11),
                    wraplength=475,
                    justify="left",
                    anchor="w",
                )
                self.release_summary_label.pack(fill="x", padx=28, pady=(0, 8))
            ctk.CTkLabel(
                shell,
                text="© 2026 GANOMABI / amiinarii",
                text_color=app_theme.color("#786757"),
                font=(FONT, 10),
            ).pack(side="bottom", pady=(0, 14))
            row = ctk.CTkFrame(shell, fg_color="transparent")
            row.pack(side="bottom", fill="x", padx=26, pady=(6, 12))
            self.download_label = ctk.CTkLabel(
                shell, text="", text_color=GOLD, font=(FONT, 11)
            )
            self.download_label.pack(fill="x", padx=28)
            self.download_progress = ctk.CTkProgressBar(
                shell, progress_color=RED, fg_color=LINE, height=5
            )
            self.download_progress.set(0)
            self.download_progress.pack(fill="x", padx=28, pady=4)

            def download():
                if self.update_installing or self.busy:
                    return
                if os.name != "nt" or not getattr(sys, "frozen", False):
                    close()
                    self.show_update_notice(
                        error=tr("Gunakan EXE Windows untuk memasang update otomatis.")
                    )
                    return
                self.update_installing = True
                self.set_update_status(tr("Menyiapkan unduhan..."))
                self.global_update_progress.grid()
                self.global_update_button.grid_remove()
                primary.configure(state="disabled", text=tr("Mengunduh..."))
                self.download_label.configure(text=tr("Menyiapkan unduhan..."))

                def worker():
                    from .auto_updater import download_update

                    try:
                        path = download_update(
                            release,
                            os.path.dirname(user_config_path()),
                            lambda value: self.results.append(
                                ("update_progress", value)
                            ),
                        )
                        self.results.append(("update_downloaded", path))
                    except Exception as exc:
                        self.results.append(("update_failed", str(exc)))

                threading.Thread(target=worker, daemon=True).start()

            def retry():
                close()
                self.check_updates(manual=True)

            action = download if release else retry if error else close
            label = (
                tr("Update sekarang")
                if release
                else tr("Coba lagi") if error else tr("Mengerti")
            )
            primary = ctk.CTkButton(
                row,
                text=label,
                command=action,
                width=180,
                height=42,
                fg_color=RED,
                hover_color=app_theme.color("#d13747"),
                text_color=app_theme.color("#ffffff"),
                corner_radius=6,
                font=(FONT, 12),
            )
            primary.pack(side="right")
            if release or error:
                ctk.CTkButton(
                    row,
                    text=tr("Nanti") if release else tr("Tutup"),
                    command=close,
                    width=120,
                    height=42,
                    fg_color=app_theme.color("#f1e3cc"),
                    hover_color=app_theme.color("#e6d0aa"),
                    text_color=WHITE,
                    border_color=LINE,
                    border_width=1,
                    corner_radius=6,
                    font=(FONT, 12),
                ).pack(side="right", padx=(0, 10))
            dialog.bind("<Return>", lambda event: action())

            self.start_update_button = primary
            dialog.lift()
            primary.focus_set()

        def finish_update_error(self, error):
            self.update_installing = False
            self.global_update_progress.grid_remove()
            if self.latest_release:
                self.global_update_button.grid()
            self.set_update_status(tr("Update gagal. EXE lama tetap tersedia."))
            if self.update_dialog is not None and self.update_dialog.winfo_exists():
                self.update_dialog.grab_release()
                self.update_dialog.destroy()
            self.update_dialog = None
            self.show_update_notice(error=error)

        def run(self, label, work):
            if self.busy or self.update_installing:
                return
            self.busy = True
            self._transfer_rate = None
            self._transfer_tick = 0
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
            self.drive_widgets["active"][0].configure(
                text=self.store.data_dir if self.store.exe else tr("Pilih FiveM.exe")
            )
            self.drive_widgets["archive"][0].configure(
                text=self.store.archive_root or tr("Semua cache di drive FiveM")
            )
            self.archive_path_label.configure(
                text=self.store.archive_root
                or tr(
                    "Belum ada folder arsip. Pilih folder di HDD untuk menghemat ruang."
                )
            )
            if os.path.isfile(self.store.journal):
                self.transfer_panel.grid()
                if not self.busy:
                    self.transfer_label.configure(
                        text=tr(
                            "Transfer tertunda. Sambungkan drive, sediakan ruang, lalu pilih Lanjutkan transfer di Peralatan."
                        )
                    )
            elif not self.busy:
                self.transfer_panel.grid_remove()
            labels = {
                None: tr("Belum ada cache aktif"),
                "external": tr("Cache lama belum terdaftar"),
                "conflict": tr("Backup perlu diperiksa"),
            }
            self.status.configure(
                text=self.store.profiles.get(
                    active, labels.get(active, tr("Belum diketahui"))
                ),
                text_color=GOLD,
            )
            if os.path.isfile(self.store.journal):
                self.status.configure(text=tr("Switch perlu dipulihkan"))
            linked = bool(
                self.store.exe
                and os.path.isfile(self.store.exe)
                and os.path.isdir(self.store.data_dir)
            )
            self.connection.configure(
                text=(
                    tr("Instalasi terhubung")
                    if linked
                    else tr("Pilih FiveM.exe untuk mulai")
                )
            )
            self.metric_count.configure(
                text=f"{len(self.store.profiles)}{tr(' PROFIL')}"
            )
            total = sum((n for n in self.raw_sizes.values() if n is not None))
            self.metric_size.configure(text=format_size(total) + tr(" tersimpan"))
            self.count.configure(
                text=f"{tr('Daftar kota')} · {len(self.store.profiles)}"
            )
            if not self.store.profiles:
                empty = ctk.CTkFrame(
                    self.list,
                    fg_color=CARD,
                    border_color=LINE,
                    border_width=1,
                    corner_radius=14,
                )
                empty.grid(row=0, column=0, columnspan=3, sticky="ew", pady=6)
                self.art(empty, "empty", CARD).pack(pady=(18, 3))
                ctk.CTkLabel(
                    empty,
                    text=tr("Belum ada profil"),
                    text_color=WHITE,
                    font=(FONT, 16, "bold"),
                ).pack()
                ctk.CTkLabel(
                    empty,
                    text=tr("Pilih FiveM.exe, lalu tambahkan kota pertamamu."),
                    text_color=MUTED,
                    font=(FONT, 11),
                ).pack(pady=(5, 20))
            for index, (pid, name) in enumerate(self.store.profiles.items()):
                current = active == pid
                bg = app_theme.color("#fae6d1") if current else CARD
                card = ctk.CTkFrame(
                    self.list,
                    fg_color=bg,
                    border_color=app_theme.color("#b68b48") if current else LINE,
                    border_width=1,
                    corner_radius=12,
                )
                card.grid(
                    row=index // 3, column=index % 3, sticky="nsew", padx=5, pady=5
                )
                card.grid_columnconfigure(0, weight=1)
                header = ctk.CTkFrame(card, fg_color="transparent")
                header.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 5))
                badge = ctk.CTkFrame(
                    header,
                    fg_color=(
                        app_theme.color("#ead0b0")
                        if current
                        else app_theme.color("#efe0c7")
                    ),
                    width=46,
                    height=46,
                    corner_radius=12,
                )
                badge.pack(side="left")
                badge.pack_propagate(False)
                ctk.CTkLabel(
                    badge,
                    text=f"{index + 1:02d}",
                    font=(FONT, 16, "bold"),
                    text_color=GOLD,
                ).pack(expand=True)
                location = self.store.profile_location(pid)
                location_names = {
                    "active": tr("DRIVE AKTIF"),
                    "local": tr("LOKAL"),
                    "archive": (
                        tr("ARSIP HDD")
                        if self.store.storage_online()
                        else tr("HDD OFFLINE")
                    ),
                    "missing": tr("BELUM ADA"),
                }
                ctk.CTkLabel(
                    header,
                    text=location_names[location],
                    text_color=GOLD if current else MUTED,
                    font=(FONT, 8, "bold"),
                ).pack(side="right", padx=(6, 0))
                info = ctk.CTkFrame(card, fg_color="transparent")
                info.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))
                short = name if len(name) <= 48 else name[:45] + "…"
                ctk.CTkLabel(
                    info,
                    text=short,
                    anchor="w",
                    font=(FONT, 13, "bold"),
                    height=38,
                    wraplength=210,
                    justify="left",
                    text_color=WHITE,
                ).pack(fill="x")
                ctk.CTkLabel(
                    info,
                    text=(tr("AKTIF  /  ") if current else "")
                    + self.sizes.get(pid, tr("Menghitung...")),
                    anchor="w",
                    text_color=GOLD if current else MUTED,
                    font=(FONT, 10),
                ).pack(fill="x", pady=(2, 0))
                actions = ctk.CTkFrame(card, fg_color="transparent")
                actions.grid(row=2, column=0, sticky="ew", padx=10, pady=(2, 12))
                actions.grid_columnconfigure(0, weight=1)
                switch = self.btn(
                    actions,
                    tr("Sedang aktif") if current else tr("Aktifkan"),
                    lambda p=pid: self.switch(p),
                    primary=not current,
                    width=96,
                    height=32,
                )
                switch.grid(row=0, column=0, sticky="ew", padx=(0, 4))
                if current:
                    switch.configure(state="disabled", text_color_disabled=GOLD)
                self.btn(
                    actions,
                    tr("Nama"),
                    lambda p=pid: self.rename(p),
                    width=36,
                    height=32,
                ).grid(row=0, column=1, sticky="ew", padx=(0, 4))
                self.btn(
                    actions,
                    tr("Hapus"),
                    lambda p=pid: self.delete(p),
                    width=36,
                    height=32,
                ).grid(row=0, column=2, sticky="ew")
            if self.busy:
                for b in self.buttons:
                    if b.winfo_exists():
                        b.configure(state="disabled")

        def refresh(self):
            if self.busy:
                return
            self.exe_label.configure(
                text=self.store.exe or tr("FiveM.exe belum dipilih")
            )
            self.path_label.configure(
                text=(
                    "CACHE  /  " + self.store.active
                    if self.store.exe
                    else tr("CACHE  /  menunggu lokasi FiveM.exe")
                )
            )
            self.size_generation += 1
            generation = self.size_generation
            active = self.store.detect()
            paths = {
                p: self.store.active if p == active else self.store.backup(p)
                for p in self.store.profiles
            }
            self.sizes, self.raw_sizes = ({}, {})
            self.render()

            def worker():
                sizes = {
                    p: folder_size(path) if os.path.isdir(path) else None
                    for p, path in paths.items()
                }
                self.results.append(("sizes", (generation, sizes)))
                import shutil

                stats = {}
                for key, path in [
                    ("active", self.store.data_dir),
                    ("archive", self.store.archive_root),
                ]:
                    try:
                        stats[key] = (
                            shutil.disk_usage(path)
                            if path and os.path.isdir(path)
                            else None
                        )
                    except OSError:
                        stats[key] = None
                self.results.append(("storage_stats", (generation, stats)))

            threading.Thread(target=worker, daemon=True).start()

        def add(self):
            try:
                self.store.validate()
            except Exception as e:
                messagebox.showinfo(tr("Hubungkan FiveM"), str(e), parent=self)
                self.change_path()
                return
            name = self.ask_profile(
                tr("Tambah kota / cache"),
                tr("Nama kota atau profil cache"),
                confirm=tr("Tambah kota"),
            )
            if name and name.strip():
                self.run(
                    tr("Membuat profil..."),
                    lambda: (self.store.add(name.strip()), tr("Profil dibuat."))[1],
                )

        def rename(self, pid):
            name = self.ask_profile(
                tr("Ubah nama profil"),
                tr("Nama kota atau profil cache"),
                initial=self.store.profiles[pid],
                confirm=tr("Simpan nama"),
            )
            if name and name.strip():
                self.run(
                    tr("Menyimpan nama..."),
                    lambda: (
                        self.store.rename(pid, name.strip()),
                        tr("Nama diperbarui."),
                    )[1],
                )

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
            card = ctk.CTkFrame(
                dialog,
                fg_color=CARD,
                border_color=LINE,
                border_width=1,
                corner_radius=14,
            )
            card.pack(fill="both", expand=True, padx=12, pady=12)
            head = ctk.CTkFrame(card, fg_color="transparent")
            head.pack(fill="x", padx=20, pady=(10, 2))
            self.art(head, "status", CARD).pack(side="left", padx=(0, 12))
            titles = ctk.CTkFrame(head, fg_color="transparent")
            titles.pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(
                titles,
                text=APP_NAME,
                text_color=GOLD,
                font=(FONT, 10, "bold"),
                anchor="w",
            ).pack(fill="x")
            ctk.CTkLabel(
                titles,
                text=title,
                text_color=WHITE,
                font=(FONT, 20, "bold"),
                anchor="w",
            ).pack(fill="x", pady=4)
            ctk.CTkLabel(
                card, text=prompt, text_color=MUTED, font=(FONT, 12), anchor="w"
            ).pack(fill="x", padx=24, pady=(8, 5))
            entry = ctk.CTkEntry(
                card,
                height=44,
                fg_color=app_theme.color("#f5ead6"),
                border_color=app_theme.color("#8e6846"),
                border_width=1,
                corner_radius=9,
                text_color=WHITE,
                placeholder_text=tr("Contoh: GANOMABI City"),
                placeholder_text_color=app_theme.color("#786757"),
                font=(FONT, 14),
            )
            entry.pack(fill="x", padx=24)
            if initial:
                entry.insert(0, initial)
            hint = ctk.CTkLabel(
                card,
                text=tr("Setiap kota memiliki cache yang terpisah."),
                text_color=MUTED,
                font=(FONT, 11),
                anchor="w",
            )
            hint.pack(fill="x", padx=24, pady=(7, 10))
            buttons = ctk.CTkFrame(card, fg_color="transparent")
            buttons.pack(fill="x", padx=24, pady=(0, 18))

            def submit(event=None):
                name = entry.get().strip()
                if not name:
                    hint.configure(
                        text=tr("Isi nama kota terlebih dahulu."),
                        text_color=app_theme.color("#ee7782"),
                    )
                    entry.focus_set()
                    return
                dialog.result = name
                dialog.destroy()

            self.btn(buttons, confirm, submit, primary=True, width=158, height=40).pack(
                side="right"
            )
            self.btn(buttons, tr("Batal"), dialog.destroy, width=110, height=40).pack(
                side="right", padx=9
            )
            dialog.bind("<Return>", submit)
            dialog.bind("<Escape>", lambda e: dialog.destroy())
            dialog.deiconify()
            dialog.wait_visibility()
            dialog.grab_set()
            dialog.after(
                80,
                lambda: (
                    (entry.focus_set(), entry.select_range(0, "end"))
                    if initial
                    else entry.focus_set()
                ),
            )
            self.wait_window(dialog)
            return dialog.result

        def switch(self, pid):
            name = self.store.profiles[pid]
            self.run(
                tr("Mengaktifkan ") + name + "...",
                lambda: (
                    self.store.switch(pid, self.transfer_update),
                    tr("Cache aktif: ") + name,
                )[1],
            )

        def delete(self, pid):
            if messagebox.askyesno(
                tr("Hapus profil"),
                tr("Hapus profil '")
                + self.store.profiles[pid]
                + tr(
                    "'?\n\nCache dipindahkan ke cache-switcher-trash dan bisa dipulihkan manual."
                ),
                parent=self,
            ):
                self.run(
                    tr("Memindahkan cache..."),
                    lambda: tr("Cache disimpan di: ") + self.store.delete(pid),
                )

        def change_path(self):
            exe = filedialog.askopenfilename(
                title=tr("Pilih FiveM.exe"),
                initialdir=(
                    os.path.dirname(self.store.exe)
                    if self.store.exe
                    else os.path.expanduser("~")
                ),
                filetypes=[("FiveM Launcher", "FiveM.exe"), ("Executable", "*.exe")],
                parent=self,
            )
            if not exe:
                return
            try:
                no_fivem()
                locations = find_data_directories(exe)
                if len(locations) == 1:
                    data = locations[0]
                else:
                    messagebox.showinfo(
                        tr("Pilih lokasi data"),
                        tr(
                            "Ada beberapa lokasi data atau folder data belum terdeteksi.\nPilih folder data yang berisi server-cache-priv milik FiveM ini."
                        ),
                        parent=self,
                    )
                    data = filedialog.askdirectory(
                        title=tr("Pilih folder data milik FiveM ini"),
                        initialdir=os.path.dirname(exe),
                        parent=self,
                    )
                    if not data:
                        return
                if (
                    self.store.profiles
                    and os.path.normcase(os.path.dirname(os.path.abspath(data)))
                    != os.path.normcase(os.path.abspath(self.store.path))
                    and (
                        not messagebox.askyesno(
                            tr("Ganti instalasi"),
                            tr(
                                "Tampilkan profil milik instalasi yang baru?\nCache instalasi sebelumnya tetap tersedia di folder asal."
                            ),
                            parent=self,
                        )
                    )
                ):
                    return
                self.run(
                    tr("Menghubungkan FiveM.exe..."),
                    lambda: (
                        self.store.select_exe(exe, data),
                        tr("FiveM terhubung. Backup kota yang ditemukan ditampilkan."),
                    )[1],
                )
            except Exception as e:
                messagebox.showerror(tr("Lokasi FiveM"), str(e), parent=self)

        def open_folder(self):
            if os.path.isdir(self.store.data_dir) and self.store.exe:
                os.startfile(self.store.data_dir)
            else:
                self.change_path()

        def launch(self):
            if self.busy or os.path.isfile(self.store.journal):
                messagebox.showinfo(
                    tr("Transfer belum selesai"),
                    tr("Selesaikan transfer sebelum menjalankan FiveM."),
                    parent=self,
                )
                return
            if self.store.exe and os.path.isfile(self.store.exe):
                try:
                    os.startfile(self.store.exe)
                except OSError as e:
                    messagebox.showerror(tr("Launch gagal"), str(e), parent=self)
            else:
                self.change_path()

        def recover(self):
            if not os.path.isfile(self.store.journal):
                messagebox.showinfo(
                    tr("Pemulihan"),
                    tr("Tidak ada switch yang perlu dipulihkan."),
                    parent=self,
                )
                return
            self.run(
                tr("Memulihkan switch..."),
                lambda: (
                    self.store.recover(self.transfer_update),
                    tr("Transfer / pemulihan selesai."),
                )[1],
            )

        def clean(self):
            choice = self.temp_choice.get()
            user = os.environ.get("TEMP", "")
            system = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "Temp")
            paths = (
                [user]
                if choice == "User Temp"
                else [system] if choice == "System Temp" else [user, system]
            )
            if messagebox.askyesno(
                tr("Bersihkan Temp"),
                tr("Hapus isi folder berikut?\n\n")
                + "\n".join(paths)
                + tr("\n\nFile yang dipakai atau terkunci akan dilewati."),
                parent=self,
            ):

                def work():
                    removed, skipped = clean_temp(paths)
                    return f"Temp: {removed}{tr(' item dibersihkan, ')}{skipped}{tr(' dilewati.')}"

                self.run(tr("Membersihkan Temp..."), work)

        def load_adapters(self):

            def worker():
                try:
                    r = subprocess.run(
                        [
                            "powershell",
                            "-NoProfile",
                            "-NonInteractive",
                            "-Command",
                            "Get-NetAdapter | Where-Object Status -eq 'Up' | Select-Object -ExpandProperty Name",
                        ],
                        capture_output=True,
                        text=True,
                        creationflags=134217728,
                        timeout=20,
                    )
                    if r.returncode == 0:
                        self.results.append(
                            (
                                "adapters",
                                [n.strip() for n in r.stdout.splitlines() if n.strip()],
                            )
                        )
                except Exception:
                    pass

            threading.Thread(target=worker, daemon=True).start()

        def dns(self):
            adapter, choice = (self.adapter.get(), self.dns_choice.get())
            if adapter == tr("Pilih adapter"):
                messagebox.showinfo(
                    tr("Adapter"),
                    tr("Tidak ada adapter aktif yang terdeteksi."),
                    parent=self,
                )
                self.load_adapters()
                return
            if messagebox.askyesno(
                tr("Ubah DNS"),
                f"""{tr('Terapkan ')}{choice}{tr(" pada adapter '")}{adapter}'?""",
                parent=self,
            ):
                self.run(
                    tr("Mengatur DNS..."),
                    lambda: (
                        set_dns(adapter, choice),
                        f"DNS {choice}{tr(' diterapkan ke ')}{adapter}.",
                    )[1],
                )

        def close(self):
            if self.update_installing:
                return
            if self.busy:
                messagebox.showinfo(
                    tr("Sedang bekerja"),
                    tr("Tunggu operasi selesai sebelum menutup aplikasi."),
                    parent=self,
                )
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
            messagebox.showinfo(APP_NAME, tr("Aplikasi sudah terbuka."))
            return
    app = App()
    if len(sys.argv) == 3 and sys.argv[1] == "--smoke-ui":
        from .frozen_ui_check import install

        install(app, sys.argv[2])
    app.mainloop()
    if mutex:
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        kernel.CloseHandle(mutex)
