# Copyright (c) 2026 GANOMABI / amiinarii.
"""Use the real UI to archive, activate, and restore temporary cache profiles."""

import os
import tempfile
import traceback
from pathlib import Path
from unittest.mock import patch
from tkinter import filedialog
import customtkinter as ctk
from ganov import ui, storage
from ganov.core import CacheStore

errors = []
completed = []
original_loop = ctk.CTk.mainloop


def loop(app):
    app.check_updates = lambda *a, **k: None
    app.load_adapters = lambda: None
    app.periodic_servers = lambda: None
    app.periodic_status = lambda: None
    app.report_callback_exception = lambda *args: errors.append(
        "".join(traceback.format_exception(*args))
    )

    def finish(error=None):
        if error:
            errors.append(str(error))
        app.closed = True
        app.destroy()

    def idle():
        import tkinter as tk

        done = tk.BooleanVar(master=app, value=False)
        app.after(100, lambda: done.set(True))
        app.wait_variable(done)

    def wait_worker():
        import time

        end = time.monotonic() + 12
        while app.busy and time.monotonic() < end:
            idle()
        assert not app.busy, "Storage worker did not finish"
        assert not errors, errors
        idle()

    def verify():
        try:
            root = Path(tmp)
            install = root / "FiveM.app"
            (install / "data").mkdir(parents=True)
            (root / "FiveM.exe").write_bytes(b"test")
            hdd = root / "HDD"
            hdd.mkdir()
            store = CacheStore(str(root / "test-config.json"), str(install))
            a, b = store.add("Jakarta"), store.add("Bandung")
            for pid, data in [(a, b"a" * 8192), (b, b"b" * 12288)]:
                (Path(store.backup(pid)) / "cache.bin").write_bytes(data)
            store.switch(a)
            app.store = store
            app.refresh()
            with patch.object(filedialog, "askdirectory", return_value=str(hdd)), patch.object(
                app, "ask_transfer", return_value=False
            ):
                app.change_archive()
                assert not store.archive_root, "Cancel changed the archive"
                assert os.path.isdir(store.local_backup(b)), "Cancel moved a cache"
            with patch.object(filedialog, "askdirectory", return_value=str(hdd)), patch.object(
                app, "ask_transfer", return_value=True
            ), patch(
                "tkinter.messagebox.showerror",
                side_effect=lambda title, text, **kw: errors.append(text),
            ), patch.object(
                storage, "same_volume", return_value=False
            ):
                app.change_archive()
                wait_worker()
                assert store.archive_root == str(hdd)
                assert os.path.isdir(store.cold_backup(b))
                assert not os.path.exists(store.local_backup(b))
                assert app.archive_path_label.cget("text") == str(hdd)
                app.switch(b)
                wait_worker()
                assert store.detect() == b
                assert (Path(store.active) / "cache.bin").read_bytes() == b"b" * 12288
                assert os.path.isdir(store.cold_backup(a))
                assert app.status.cget("text") == "Bandung"
                assert not app.transfer_panel.winfo_viewable()
                assert any(
                    w.cget("text") == "ARSIP HDD"
                    for card in app.list.winfo_children()
                    for child in card.winfo_children()
                    for w in child.winfo_children()
                    if isinstance(w, ctk.CTkLabel)
                )
                app.show_page("tools")
                app.disable_archive()
                wait_worker()
                assert not store.archive_root
                assert os.path.isdir(store.local_backup(a))
                app.busy = True
                with patch("tkinter.messagebox.showinfo") as blocked:
                    app.launch()
                    assert (
                        blocked.called
                    ), "Launching FiveM was not blocked during transfer"
                app.busy = False
                app.show_page("cache")
                app.change_language("English")
                assert app.nav["cache"].cget("text") == "City profiles"
                assert "All caches" in app.drive_widgets["archive"][0].cget("text")
                app.change_theme("Dark")
                assert app.archive_path_label.winfo_exists()
                app.geometry("1040x760")
                idle()
            completed.append(True)
            finish()
        except Exception:
            traceback.print_exc()
            finish(traceback.format_exc())

    app.after(1000, verify)
    app.after(45000, lambda: finish("Storage UI timed out"))
    original_loop(app)


with tempfile.TemporaryDirectory() as tmp:
    os.environ["LOCALAPPDATA"] = tmp
    # The real UI stores its imported tkinter objects locally, so patch tkinter's functions.
    ctk.CTk.mainloop = loop
    try:
        ui.main()
    finally:
        ctk.CTk.mainloop = original_loop
if errors or not completed:
    raise AssertionError(errors or "Storage UI checks did not run")
print(
    "PASS: real UI HDD migration, byte-preserving activation, return to local storage, launch guard, English and dark theme."
)

