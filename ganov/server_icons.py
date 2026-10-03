"""Download FiveM server logos off the UI thread, with a small disk cache."""

from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
from urllib.request import Request, urlopen

from PIL import Image, ImageOps
from .server_catalog import connect_uri

MAX_BYTES = 2 * 1024 * 1024


def decode_icon(raw):
    if len(raw) > MAX_BYTES:
        raise ValueError("Server icon too large")
    with Image.open(BytesIO(raw)) as image:
        if image.format != "PNG" or not (
            1 <= image.width <= 512 and 1 <= image.height <= 512
        ):
            raise ValueError("Invalid server icon")
        image.load()
        return ImageOps.pad(image.convert("RGBA"), (64, 64), color=(0, 0, 0, 0))


def load_icon(code, version, cache):
    connect_uri(code)
    directory = Path(cache)
    valid_version = (
        type(version) is int and -(2**31) <= version < 2**32 and version != 0
    )
    target = directory / f"{code}_{version}.png" if valid_version else None
    if target and target.exists():
        try:
            return decode_icon(target.read_bytes())
        except (OSError, ValueError):
            pass
    if target:
        try:
            request = Request(
                f"https://frontend.cfx-services.net/api/servers/icon/{code}/{version}.png",
                headers={"User-Agent": "GanoV-Cache-Switch"},
            )
            with urlopen(request, timeout=12) as response:
                raw = response.read(MAX_BYTES + 1)
            image = decode_icon(raw)
            try:
                directory.mkdir(parents=True, exist_ok=True)
                temporary = target.with_suffix(".new")
                temporary.write_bytes(raw)
                temporary.replace(target)
                for previous in directory.glob(f"{code}_*.png"):
                    if previous != target:
                        previous.unlink(missing_ok=True)
            except OSError:
                pass
            return image
        except (OSError, ValueError):
            pass
    # Keep the last valid logo when the server or icon service is offline.
    for previous in directory.glob(f"{code}_*.png"):
        try:
            return decode_icon(previous.read_bytes())
        except (OSError, ValueError):
            pass
    return None


def fetch_icons(statuses, cache):
    def fetch(item):
        code, status = item
        try:
            return code, load_icon(code, status.get("icon_version"), cache)
        except Exception:
            return code, None

    with ThreadPoolExecutor(max_workers=4) as executor:
        return {
            code: image
            for code, image in executor.map(fetch, statuses.items())
            if image is not None
        }
