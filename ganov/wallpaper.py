"""Quiet wallpaper layers behind application controls."""

import tkinter as tk
from PIL import Image, ImageOps, ImageEnhance, ImageTk


class Wallpaper:
    def __init__(self, parent, path, theme):
        self.parent = parent
        self.pending = None
        self.text_widgets = []
        self.tint = "#101113" if theme == "dark" else "#f7f0e3"
        parent._wallpaper_layer = self
        with Image.open(path) as source:
            self.source = source.convert("RGB")
        self.source = ImageEnhance.Color(self.source).enhance(0.65)
        self.theme = theme
        self.canvas_mode = isinstance(parent, tk.Canvas)
        self.label = (
            parent
            if self.canvas_mode
            else tk.Label(
                parent,
                borderwidth=0,
                highlightthickness=0,
                background="#101113" if theme == "dark" else "#f7f0e3",
            )
        )
        if self.canvas_mode:
            parent.configure(background=self.tint)
            self.image_item = parent.create_image(0, 0, anchor="nw")
            parent.tag_lower(self.image_item)
        else:
            self.label.place(x=0, y=0, relwidth=1, relheight=1)
        self.binding = self.label.bind("<Configure>", self.schedule, add="+")
        self.label.bind("<Destroy>", self.cleanup, add="+")
        self.schedule()

    def schedule(self, event=None):
        if event is not None and event.widget is not self.label:
            return
        if self.pending:
            self.parent.after_cancel(self.pending)
        self.pending = self.parent.after(100, self.paint)

    def paint(self):
        self.pending = None
        if not self.label.winfo_exists():
            return
        size = (max(1, self.label.winfo_width()), max(1, self.label.winfo_height()))
        image = ImageOps.fit(self.source, size, method=Image.Resampling.LANCZOS)
        tint = "#101113" if self.theme == "dark" else "#f7f0e3"
        # Strong tint keeps the artwork soft and the interface readable.
        image = Image.blend(
            image, Image.new("RGB", size, tint), 0.91 if self.theme == "dark" else 0.95
        )
        self.rendered = image
        self.photo = ImageTk.PhotoImage(image, master=self.parent)
        if self.canvas_mode:
            self.parent.itemconfigure(self.image_item, image=self.photo)
            self.parent.tag_lower(self.image_item)
        else:
            self.label.configure(image=self.photo)
        for widget in list(self.text_widgets):
            if widget.winfo_exists():
                widget.repaint()
            else:
                self.text_widgets.remove(widget)

    def cleanup(self, event):
        if event.widget is not self.label:
            return
        if self.pending:
            self.parent.after_cancel(self.pending)
            self.pending = None
        if self.binding:
            self.label.unbind("<Configure>", self.binding)
            self.binding = None


class WallpaperText(tk.Canvas):
    """Draw text directly over a wallpaper crop instead of an opaque label."""

    def __init__(
        self,
        parent,
        layer,
        text="",
        text_color="#ffffff",
        font=("Segoe UI", 12),
        anchor="center",
        wraplength=0,
        justify="center",
        height=28,
        width=0,
        **kwargs
    ):
        import customtkinter as ctk
        from tkinter import font as tkfont

        self.layer = layer
        self.text = text
        self.color = text_color
        self.anchor = anchor
        self.wraplength = wraplength
        scale = ctk.ScalingTracker.get_widget_scaling(parent)
        self.text_font = tkfont.Font(
            family=font[0],
            size=-round(font[1] * scale),
            weight="bold" if len(font) > 2 and font[2] == "bold" else "normal",
        )
        requested = (
            min(self.text_font.measure(text) + 4, round(wraplength * scale))
            if wraplength
            else self.text_font.measure(text) + 4
        )
        super().__init__(
            parent,
            width=max(round(width * scale), requested),
            height=round(height * scale),
            background=layer.tint,
            borderwidth=0,
            highlightthickness=0,
        )
        self.justify = justify
        layer.text_widgets.append(self)
        self.bind("<Configure>", lambda event: self.repaint(), add="+")
        self.bind("<Map>", lambda event: self.after_idle(self.repaint), add="+")

    def repaint(self):
        if not self.winfo_exists() or not hasattr(self.layer, "rendered"):
            return
        x = self.winfo_rootx() - self.layer.label.winfo_rootx()
        y = self.winfo_rooty() - self.layer.label.winfo_rooty()
        width, height = self.winfo_width(), self.winfo_height()
        crop = self.layer.rendered.crop((x, y, x + width, y + height))
        self.background_photo = ImageTk.PhotoImage(crop, master=self)
        self.delete("all")
        self.create_image(0, 0, image=self.background_photo, anchor="nw")
        left = self.anchor in ("w", "nw", "sw")
        if hasattr(self, "art_image"):
            import customtkinter as ctk

            scale = ctk.ScalingTracker.get_widget_scaling(self.master)
            art_width, art_height = getattr(self, "art_size", (90, 60))
            icon = ImageOps.contain(
                self.art_image, (round(art_width * scale), round(art_height * scale))
            )
            self.art_photo = ImageTk.PhotoImage(icon, master=self)
            self.create_image(width / 2, height / 2, image=self.art_photo)
        self.create_text(
            2 if left else width / 2,
            height / 2,
            text=self.text,
            fill=self.color,
            font=self.text_font,
            anchor="w" if left else "center",
            justify=self.justify,
            width=max(1, width - 4),
        )

    def cget(self, key):
        if key == "text":
            return self.text
        if key == "text_color":
            return self.color
        return super().cget(key)

    def configure(self, cnf=None, **kwargs):
        if "text" in kwargs:
            self.text = kwargs.pop("text")
            kwargs["width"] = max(1, self.text_font.measure(self.text) + 4)
        if "text_color" in kwargs:
            self.color = kwargs.pop("text_color")
        result = super().configure(cnf, **kwargs)
        if hasattr(self, "layer"):
            self.repaint()
        return result

