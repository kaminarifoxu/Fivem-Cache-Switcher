# Copyright (c) 2026 GANOMABI / amiinarii.
"""Rebuild using the Python 3.14 runtime already bundled in the supplied EXE.

Run with Python 3.14. Does not run the original application's code.
"""
import argparse
import marshal
from pathlib import Path
import struct
import sys
import zlib
from win_resources import patch_resources
from cache_switcher import VERSION

MAGIC = b"MEI\x0c\x0b\x0a\x0b\x0e"


def rebuild(original, source, destination):
    data = Path(original).read_bytes()
    cookie_pos = data.rfind(MAGIC)
    if cookie_pos < 0:
        raise ValueError("Not a PyInstaller executable")
    magic, size, toc_offset, toc_size, version, library = struct.unpack("!8sIIII64s", data[cookie_pos:cookie_pos + 88])
    if version != 314 or sys.version_info[:2] != (3, 14):
        raise RuntimeError("This executable requires Python 3.14 to rebuild")
    start = cookie_pos + 88 - size
    pos, end = start + toc_offset, start + toc_offset + toc_size
    records = []
    replaced = False
    source_code = Path(source).read_text(encoding="utf-8")
    compiled = marshal.dumps(compile(source_code, "cache_switcher.py", "exec"))
    while pos < end:
        length, offset, compressed_size, plain_size, flag, kind = struct.unpack("!IIIIBc", data[pos:pos + 18])
        name = data[pos + 18:pos + length].rstrip(b"\0")
        pos += length
        chunk = data[start + offset:start + offset + compressed_size]
        if kind == b"s" and name == b"fivem_cache_switcher":
            chunk = zlib.compress(compiled, 9)
            flag, plain_size = 1, len(compiled)
            replaced = True
        records.append((name, kind, flag, plain_size, chunk))
    if not replaced:
        raise ValueError("Application entry point was not found")
    assets = Path(source).parent / "assets"
    for asset in sorted(assets.rglob("*")):
        if asset.is_file():
            name = ("assets/" + asset.relative_to(assets).as_posix()).replace("/", "\\").encode()
            chunk = asset.read_bytes()
            records.append((name, b"b", 1, len(chunk), zlib.compress(chunk, 9)))
    payload, toc = bytearray(), bytearray()
    for name, kind, flag, plain_size, chunk in records:
        offset = len(payload)
        payload.extend(chunk)
        record_size = (18 + len(name) + 1 + 15) & ~15
        toc.extend(struct.pack("!IIIIBc", record_size, offset, len(chunk), plain_size, flag, kind))
        toc.extend(name + b"\0" * (record_size - 18 - len(name)))
    new_cookie = struct.pack("!8sIIII64s", magic, len(payload) + len(toc) + 88, len(payload), len(toc), version, library)
    bootloader = patch_resources(data[:start], (assets / "ganomabi.ico").read_bytes(), version=VERSION)
    Path(destination).write_bytes(bootloader + payload + toc + new_cookie)
    print("Created:", destination)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("original", help="Path to the original FiveM Cache Switcher.exe")
    parser.add_argument("--source", default=str(Path(__file__).with_name("cache_switcher.py")))
    parser.add_argument("--output", default=str(Path(__file__).with_name("GanoV-Cache-Switch.exe")))
    args = parser.parse_args()
    rebuild(args.original, args.source, args.output)
