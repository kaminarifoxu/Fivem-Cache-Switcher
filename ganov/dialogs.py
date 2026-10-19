# Copyright (c) 2026 GANOMABI / amiinarii.
"""Theme-aware storage confirmations. No filesystem operations occur here."""

import os
import tkinter as tk
import customtkinter as ctk
from . import app_theme
from .i18n import tr


class TransferDialog(ctk.CTkToplevel):
    def __init__(self, parent, title, description, folder, returning=False):
        super().__init__(parent)
        self.withdraw()
        self.result = False
        self.parent = parent
        self.title(title + " | GanoV")
        self.transient(parent)
        self.resizable(False, False)
        color = app_theme.color
        bg, card, line = color("#f7f0e3"), color("#fffaf1"), color("#ddc8a3")
        text, muted, gold = color("#30251e"), color("#786757"), color("#896019")
        font = "Segoe UI" if os.name == "nt" else "DejaVu Sans"
        self.configure(fg_color=bg)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        # Keep actions visible on a short screen; the description/path can scroll.
        header = ctk.CTkFrame(self, fg_color=card, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        ctk.CTkFrame(header, height=4, fg_color="#b82736", corner_radius=0).pack(fill="x")
        brand = ctk.CTkFrame(header, fg_color="transparent")
        brand.pack(fill="x", padx=26, pady=20)
        ctk.CTkLabel(brand, text="G", width=42, height=42, corner_radius=12,
                     fg_color="#b82736", text_color="#ffffff", font=(font, 23, "bold")).pack(side="left", padx=(0, 12))
        headings = ctk.CTkFrame(brand, fg_color="transparent")
        headings.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(headings, text="GANOMABI  /  CACHE SWITCH", anchor="w",
                     text_color=gold, font=(font, 11, "bold")).pack(fill="x")
        ctk.CTkLabel(headings, text=tr("Penyimpanan SSD / HDD"), anchor="w",
                     text_color=muted, font=(font, 12)).pack(fill="x", pady=(3, 0))
        body = ctk.CTkScrollableFrame(self, fg_color=bg, corner_radius=0)
        body.grid(row=1, column=0, sticky="nsew", padx=14, pady=(12, 0))
        body.grid_columnconfigure(0, weight=1)
        self.heading = ctk.CTkLabel(body, text=title, anchor="w", justify="left",
                                    wraplength=470, text_color=text, font=(font, 23, "bold"))
        self.heading.grid(row=0, column=0, sticky="ew", padx=12, pady=(4, 8))
        ctk.CTkLabel(body, text=description, anchor="w", justify="left", wraplength=465,
                     text_color=muted, font=(font, 13)).grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 18))
        flow = ctk.CTkFrame(body, fg_color=card, border_color=line, border_width=1, corner_radius=12)
        flow.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 14))
        flow.grid_columnconfigure((0, 2), weight=1, uniform="drive")
        source = tr("ARSIP HDD") if returning else tr("CACHE NONAKTIF")
        destination = tr("DRIVE FIVEM") if returning else tr("ARSIP HDD")
        for column, label in [(0, source), (2, destination)]:
            ctk.CTkLabel(flow, text=label, text_color=text, font=(font, 12, "bold"),
                         wraplength=180).grid(row=0, column=column, padx=12, pady=18, sticky="ew")
        ctk.CTkLabel(flow, text="→", text_color=gold, font=(font, 25)).grid(row=0, column=1)
        path_card = ctk.CTkFrame(body, fg_color=card, border_color=line, border_width=1, corner_radius=12)
        path_card.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 14))
        ctk.CTkLabel(path_card, text=tr("LOKASI TUJUAN"), text_color=gold,
                     font=(font, 10, "bold"), anchor="w").pack(fill="x", padx=14, pady=(12, 4))
        self.path_box = ctk.CTkTextbox(path_card, height=68, fg_color="transparent",
                                      text_color=text, border_width=0, wrap="char", font=(font, 12))
        self.path_box.pack(fill="x", padx=10, pady=(0, 10))
        self.path_box.insert("1.0", folder)
        self.path_box.configure(state="disabled")
        ctk.CTkLabel(body, text=tr("Tutup FiveM dan biarkan kedua drive tersambung selama transfer."),
                     text_color=muted, font=(font, 12), anchor="w", justify="left",
                     wraplength=465).grid(row=4, column=0, sticky="ew", padx=12, pady=(0, 10))
        footer = ctk.CTkFrame(self, fg_color=card, corner_radius=0)
        footer.grid(row=2, column=0, sticky="ew")
        footer.grid_columnconfigure((0, 1), weight=1, uniform="action")
        self.cancel_button = ctk.CTkButton(footer, text=tr("Batal"), height=42,
                                          fg_color=bg, hover_color=color("#efe0c7"), text_color=text,
                                          border_width=1, border_color=line, font=(font, 13),
                                          command=lambda: self.finish(False))
        self.cancel_button.grid(row=0, column=0, sticky="ew", padx=(26, 6), pady=20)
        self.confirm_button = ctk.CTkButton(footer, text=tr("Kembalikan cache") if returning else tr("Pindahkan cache"),
                                           height=42, fg_color="#b82736", hover_color="#96202d",
                                           text_color="#ffffff", font=(font, 13, "bold"), command=lambda: self.finish(True))
        self.confirm_button.grid(row=0, column=1, sticky="ew", padx=(6, 26), pady=20)
        self.protocol("WM_DELETE_WINDOW", lambda: self.finish(False))
        self.bind("<Escape>", lambda event: self.finish(False))
        self.cancel_button.bind("<Return>", lambda event: self.finish(False))
        self.confirm_button.bind("<Return>", lambda event: self.finish(True))
        scale = ctk.ScalingTracker.get_window_scaling(self)
        width, height = 560, min(610, max(340, int(parent.winfo_screenheight() / scale) - 100))
        x = parent.winfo_rootx() + (parent.winfo_width() - round(width * scale)) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - round(height * scale)) // 2
        x = max(0, min(x, parent.winfo_screenwidth() - round(width * scale)))
        y = max(0, min(y, parent.winfo_screenheight() - round(height * scale)))
        self.geometry(f"{width}x{height}+{x}+{y}")

    def finish(self, accepted):
        self.result = bool(accepted)
        if self.winfo_exists():
            self.grab_release()
            self.destroy()
        return "break"

    def show(self):
        try:
            self.deiconify()
            self.wait_visibility()
            self.grab_set()
            self.cancel_button.focus_set()
            self.parent.wait_window(self)
        except tk.TclError:
            # Closing the app while a confirmation is open must not approve work.
            self.result = False
        return self.result


def ask_transfer(parent, title, description, folder, returning=False):
    return TransferDialog(parent, title, description, folder, returning).show()
