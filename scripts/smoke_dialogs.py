# Copyright (c) 2026 GANOMABI / amiinarii.
"""Exercise real modal confirmation actions and capture both app themes."""
import os
import tempfile
from pathlib import Path
import customtkinter as ctk
from PIL import ImageGrab
from ganov import app_theme, i18n
from ganov.dialogs import ask_transfer, TransferDialog


def main():
    errors = []
    root = ctk.CTk()
    root.geometry("1000x800+20+20")
    root.update()
    output = Path("artifacts/dialogs")
    output.mkdir(parents=True, exist_ok=True)
    original_theme, original_language = app_theme.THEME, i18n.LANGUAGE
    folder = "D:/FiveM/Fivem Cache/" + "Kota dengan nama panjang — 测试/" * 6
    try:
        for theme, language, action in [
            ("light", "id", "confirm"),
            ("dark", "en", "cancel"),
            ("dark", "id", "close"),
            ("light", "en", "escape"),
        ]:
            app_theme.THEME = theme
            i18n.LANGUAGE = language
            ctk.set_appearance_mode(theme)
            root.configure(fg_color=app_theme.color("#f7f0e3"))
            returning = action in ("close", "escape")

            def inspect():
                dialogs = [w for w in root.winfo_children() if isinstance(w, TransferDialog)]
                if not dialogs:
                    errors.append("Confirmation never opened")
                    root.after(100, root.quit)
                    return
                dialog = dialogs[0]
                try:
                    assert dialog.grab_current() == dialog, "Confirmation is not modal"
                    assert dialog.result is False, "Confirmation starts approved"
                    assert dialog.path_box.get("1.0", "end-1c") == folder
                    assert dialog.path_box.cget("state") == "disabled"
                    assert dialog.confirm_button.cget("text") == i18n.tr("Kembalikan cache" if returning else "Pindahkan cache")
                    assert dialog.cancel_button.winfo_rooty() + dialog.cancel_button.winfo_height() < dialog.winfo_rooty() + dialog.winfo_height()
                    assert dialog.confirm_button.winfo_rootx() + dialog.confirm_button.winfo_width() <= dialog.winfo_rootx() + dialog.winfo_width()
                    if action in ("confirm", "cancel"):
                        bbox = (dialog.winfo_rootx(), dialog.winfo_rooty(), dialog.winfo_rootx() + dialog.winfo_width(), dialog.winfo_rooty() + dialog.winfo_height())
                        ImageGrab.grab(bbox=bbox).save(output / f"transfer-{theme}-{language}.png")
                    if action == "confirm":
                        dialog.confirm_button.invoke()
                    elif action == "cancel":
                        dialog.cancel_button.invoke()
                    elif action == "close":
                        dialog.tk.call(dialog.protocol("WM_DELETE_WINDOW"))
                    else:
                        dialog.event_generate("<Escape>")
                        if dialog.winfo_exists():
                            raise AssertionError("Escape did not cancel")
                except Exception as error:
                    errors.append(str(error))
                    if dialog.winfo_exists():
                        dialog.finish(False)

            root.after(350, inspect)
            result = ask_transfer(root, i18n.tr("Kembalikan cache ke drive FiveM?" if returning else "Pindahkan cache nonaktif?"),
                                  i18n.tr("Semua cache nonaktif akan disalin kembali. Pastikan ruang drive FiveM cukup." if returning else "Hanya cache kota nonaktif yang dipindahkan. Cache aktif tetap di drive FiveM."), folder, returning)
            assert result is (action == "confirm"), (action, result, errors)
            assert root.grab_current() is None, "Modal grab was not released"
        assert not errors, errors
    finally:
        app_theme.THEME, i18n.LANGUAGE = original_theme, original_language
        root.destroy()
    print("PASS: themed storage dialog, long Unicode path, confirm, cancel, window close, Escape, Indonesian and English.")


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as temporary:
        os.environ["LOCALAPPDATA"] = temporary
        main()
