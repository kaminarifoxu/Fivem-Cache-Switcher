# Copyright (c) 2026 GANOMABI / amiinarii.
"""Exercise the real Tk UI in both languages without opening FiveM or making network requests."""

import os
import traceback
from pathlib import Path
import tempfile
import customtkinter as ctk
from ganov import ui as cache_switcher

errors = []
original = ctk.CTk.mainloop


def automated_loop(self):
    self.check_updates = lambda *a, **k: None
    self.load_adapters = lambda: None
    self.periodic_servers = lambda: None
    self.periodic_status = lambda: None
    self.report_callback_exception = lambda *args: errors.append(args)

    def verify():
        try:
            assert self.nav["servers"].cget("text") == "Daftar server"
            assert len(self.wallpaper_layers) >= 5
            assert self.sidebar_chibi.art_image.mode == "RGBA"
            assert self.sidebar_chibi.art_size == (160, 170)

            def verify_wallpaper_resize():
                import tkinter as tk

                self.update_idletasks()
                finished = tk.BooleanVar(master=self, value=False)
                self.after(350, lambda: finished.set(True))
                self.wait_variable(finished)
                for layer in self.wallpaper_layers:
                    if layer.label.winfo_viewable():
                        assert (
                            layer.photo.width() == layer.label.winfo_width()
                        ), "wallpaper leaves unpainted horizontal area"
                        assert (
                            layer.photo.height() == layer.label.winfo_height()
                        ), "wallpaper leaves unpainted vertical area"
                        assert layer.label.cget("background") == (
                            "#101113" if layer.theme == "dark" else "#f7f0e3"
                        )

            verify_wallpaper_resize()
            self.geometry("1040x760")
            verify_wallpaper_resize()
            self.geometry("1180x820")
            verify_wallpaper_resize()
            assert self.language_selector.master.master is self.pages["tools"]
            assert self.exe_label.master.master is self.pages["tools"]
            assert self.update_status.master.master is self.pages["tools"]

            def labels(widget):
                result = []
                for child in widget.winfo_children():
                    try:
                        result.append(child.cget("text"))
                    except Exception:
                        pass
                    result.extend(labels(child))
                return result

            assert "Pilih FiveM.exe" not in labels(self.sidebar)
            assert "Cek update" not in labels(self.sidebar)
            assert "List server" in labels(self.pages["servers"])
            original_profiles = self.store.profiles.copy()
            self.store.profiles = {f"test{i}": f"CITY PROFILE {i}" for i in range(7)}
            self.render()
            cards = self.list.winfo_children()
            assert len(cards) == 7
            assert [
                (int(card.grid_info()["row"]), int(card.grid_info()["column"]))
                for card in cards
            ] == [(i // 3, i % 3) for i in range(7)]
            original_switch = self.switch
            switched = []
            self.switch = switched.append
            first_actions = cards[0].grid_slaves(row=2, column=0)[0]
            first_actions.grid_slaves(row=0, column=0)[0].invoke()
            assert switched == ["test0"], "profile card activates the wrong city"
            self.switch = original_switch
            self.change_theme("Gelap")
            verify_wallpaper_resize()
            assert len(self.list.winfo_children()) == 7
            self.change_theme("Terang")
            self.store.profiles = original_profiles
            self.render()

            self.animations_enabled = True
            self.show_page("servers")
            self.show_page("cache")
            self.show_page("tools")
            import tkinter as tk

            done = tk.BooleanVar(master=self, value=False)
            self.after(300, lambda: done.set(True))
            self.wait_variable(done)
            assert self.page_animation is None
            assert self.page == "tools"
            self.show_page("servers")
            assert not isinstance(self.server_list, ctk.CTkScrollableFrame)
            assert len(self.server_list.winfo_children()) == 9
            self.change_server_page(1)
            assert self.server_page == 1
            assert len(self.server_list.winfo_children()) == 9
            self.change_server_page(99)
            assert self.server_page == 2
            assert len(self.server_list.winfo_children()) == 7
            self.change_server_page(-99)
            assert self.server_page == 0
            self.show_page("tools")
            self.change_theme("Gelap")
            assert self.cget("fg_color") == "#101113"
            assert self.page == "tools"
            self.change_theme("Terang")
            assert self.cget("fg_color") == "#f7f0e3"
            self.show_page("servers")
            calls = []
            self.check_updates = lambda **kwargs: calls.append(kwargs)
            self.show_page("tools")
            self.check_update_button.invoke()
            assert calls == [{"manual": True}]
            self.show_page("servers")
            self.latest_release = {
                "version": "99.0.0",
                "summary": "• New theme\n• Update button fix",
            }
            self.set_update_status("Update tersedia: v99.0.0")
            self.update_idletasks()
            assert self.update_banner.winfo_viewable(), "global update banner hidden"
            self.global_update_button.invoke()
            self.update_idletasks()
            assert isinstance(self.update_dialog, ctk.CTkFrame)
            assert self.update_dialog.winfo_viewable(), "inline update panel hidden"
            assert self.grab_current() is None
            assert "Update button fix" in self.release_summary_label.cget("text")
            self.update_dialog.place_forget()
            self.show_page("tools")
            self.check_update_button.invoke()
            self.update_idletasks()
            assert self.update_dialog.winfo_viewable()
            self.show_page("servers")
            self.update_dialog.destroy()
            self.update_dialog = None
            self.change_language("English")
            assert self.nav["servers"].cget("text") == "Server list"
            assert self.page == "servers"
            self.update_idletasks()
            assert self.update_banner.winfo_viewable(), "global update banner hidden"
            self.results.append(("update_progress", 0.5))
            self.poll()
            self.update_idletasks()
            assert (
                self.global_update_progress.winfo_viewable()
            ), "global download progress hidden"
            assert self.global_update_progress.get() == 0.5
            assert len(self.catalog["servers"]) >= 5
            from PIL import Image

            self.server_icons = {
                self.catalog["servers"][0]["join_code"]: Image.new(
                    "RGBA", (64, 64), "red"
                )
            }
            self.render_servers()
            assert len(self.server_logo_images) == 1, "server logo not rendered"
            self.change_theme("Gelap")
            assert len(self.server_logo_images) == 1
            self.change_theme("Terang")
            self.server_statuses = {
                self.catalog["servers"][0]["join_code"]: {
                    "available": True,
                    "clients": 123,
                    "maximum": 2048,
                    "description": "Official description",
                    "checked": "12:00:00",
                }
            }
            self.render_servers()
            self.change_language("Indonesia")
            assert self.nav["servers"].cget("text") == "Daftar server"
            self.show_page("tools")
            self.update_idletasks()
            from unittest.mock import patch
            import threading

            invoked = threading.Event()

            def failed_download(*args):
                invoked.set()
                raise OSError("Controlled offline test")

            self.global_update_button.invoke()
            with patch.object(cache_switcher.sys, "frozen", True, create=True), patch(
                "ganov.auto_updater.download_update", side_effect=failed_download
            ):
                self.start_update_button.invoke()
                assert invoked.wait(3), "download handler did not start"
                assert self.update_installing
            import time

            deadline = time.monotonic() + 3
            while (
                not any(kind == "update_failed" for kind, _ in self.results)
                and time.monotonic() < deadline
            ):
                time.sleep(0.01)
            self.poll()
            assert not self.update_installing
            self.update_idletasks()
        except Exception as exc:
            traceback.print_exc()
            errors.append(exc)
        finally:
            self.after(500, self.close)

    self.after(1800, verify)
    self.after(10000, self.close)
    original(self)


with tempfile.TemporaryDirectory() as tmp:
    os.environ["LOCALAPPDATA"] = tmp
    ctk.CTk.mainloop = automated_loop
    try:
        cache_switcher.main()
    finally:
        ctk.CTk.mainloop = original
if errors:
    raise AssertionError(errors)
print("PASS: language switching, catalog UI, and page navigation.")
