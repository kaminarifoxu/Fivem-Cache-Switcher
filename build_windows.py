# Copyright (c) 2026 GANOMABI / amiinarii.
"""Build the standalone Windows EXE with metadata from the application version."""
from pathlib import Path
from cache_switcher import VERSION, APP_NAME, COPYRIGHT, stable_version


def build():
    import PyInstaller.__main__
    root = Path(__file__).resolve().parent
    version = (*stable_version(VERSION), 0)
    values = {
        "CompanyName": "GANOMABI / amiinarii", "FileDescription": APP_NAME,
        "FileVersion": VERSION, "InternalName": APP_NAME, "LegalCopyright": COPYRIGHT,
        "OriginalFilename": APP_NAME + ".exe", "ProductName": APP_NAME, "ProductVersion": VERSION,
    }
    root.joinpath("build").mkdir(exist_ok=True)
    metadata = root / "build" / "version_info.txt"
    strings = ",\n".join("StringStruct(" + repr(k) + ", " + repr(v) + ")" for k, v in values.items())
    metadata.write_text(
        f"VSVersionInfo(ffi=FixedFileInfo(filevers={version!r}, prodvers={version!r}, "
        "mask=0x3f, flags=0, OS=0x40004, fileType=0x1, subtype=0, date=(0, 0)), "
        "kids=[StringFileInfo([StringTable('040904B0', [" + strings + "])]), "
        "VarFileInfo([VarStruct('Translation', [1033, 1200])])])", encoding="utf-8")
    PyInstaller.__main__.run([
        "--noconfirm", "--clean", "--onefile", "--windowed", "--collect-all", "customtkinter",
        "--add-data", str(root / "assets") + ";assets", "--icon", str(root / "assets" / "ganomabi.ico"),
        "--version-file", str(metadata), "--name", APP_NAME, str(root / "cache_switcher.py"),
    ])


if __name__ == "__main__":
    build()
