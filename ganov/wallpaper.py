"""Quiet wallpaper layers behind application controls."""

import tkinter as tk
from PIL import Image, ImageOps, ImageEnhance, ImageTk


class Wallpaper:
    def __init__(self, parent, path, theme):
        self.parent = parent
        self.pending = None
        with Image.open(path) as source:
            self.source = source.convert("RGB")
        self.source = ImageEnhance.Color(self.source).enhance(0.65)
        self.theme = theme
        self.label = tk.Label(parent, borderwidth=0, highlightthickness=0)
        self.label.place(x=0, y=0, relwidth=1, relheight=1)
        self.binding = parent.bind("<Configure>", self.schedule, add="+")
        self.label.bind("<Destroy>", self.cleanup, add="+")
        self.schedule()

    def schedule(self, event=None):
        if event is not None and event.widget is not self.parent:
            return
        if self.pending:
            self.parent.after_cancel(self.pending)
        self.pending = self.parent.after(100, self.paint)

    def paint(self):
        self.pending = None
        if not self.label.winfo_exists():
            return
        size = (max(1, self.parent.winfo_width()), max(1, self.parent.winfo_height()))
        image = ImageOps.fit(self.source, size, method=Image.Resampling.LANCZOS)
        tint = "#101113" if self.theme == "dark" else "#f7f0e3"
        # Strong tint keeps the artwork soft and the interface readable.
        image = Image.blend(
            image, Image.new("RGB", size, tint), 0.76 if self.theme == "dark" else 0.87
        )
        self.photo = ImageTk.PhotoImage(image, master=self.parent)
        self.label.configure(image=self.photo)

    def cleanup(self, event):
        if event.widget is not self.label:
            return
        if self.pending:
            self.parent.after_cancel(self.pending)
            self.pending = None
        if self.binding:
            self.parent.unbind("<Configure>", self.binding)
            self.binding = None
