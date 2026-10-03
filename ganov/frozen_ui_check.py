# Copyright (c) 2026 GANOMABI / amiinarii.
import json
from pathlib import Path
import traceback


def install(app, output):
    errors = []
    app.check_updates = lambda *a, **k: None
    app.periodic_servers = lambda: None
    app.periodic_status = lambda: None
    app.load_adapters = lambda: None
    app.report_callback_exception = lambda *args: errors.append(
        "".join(traceback.format_exception(*args))
    )

    def click():
        try:
            app.latest_release = {"version": "99.0.0", "summary": "• Packaged UI test"}
            app.set_update_status("Update available: v99.0.0")
            from PIL import Image

            app.server_icons = {
                app.catalog["servers"][0]["join_code"]: Image.new(
                    "RGBA", (64, 64), "red"
                )
            }
            app.render_servers()
            app.show_page("servers")
            assert len(app.server_logo_images) == 1, "Packaged server logo not rendered"
            app.update_idletasks()
            app.global_update_button._canvas.event_generate("<Button-1>", x=30, y=15)
            app.after(500, verify)
        except Exception:
            errors.append(traceback.format_exc())
            finish()

    def verify():
        try:
            assert (
                app.update_dialog is not None and app.update_dialog.winfo_viewable()
            ), "Update panel did not appear after mouse click"
            assert (
                app.start_update_button.winfo_viewable()
            ), "Download button not visible"
            assert "Packaged UI test" in app.release_summary_label.cget("text")
        except Exception:
            errors.append(traceback.format_exc())
        finish()

    def finish():
        Path(output).write_text(
            json.dumps({"ok": not errors, "errors": errors}), encoding="utf-8"
        )
        app.close()

    app.after(2000, click)
