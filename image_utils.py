import io
import math
import requests
from PIL import Image

TARGET_W, TARGET_H = 3840, 2160


def _get_image_dimensions(iiif_url: str) -> tuple[int, int]:
    r = requests.get(f"{iiif_url}/info.json", timeout=30)
    r.raise_for_status()
    info = r.json()
    return info["width"], info["height"]


def download_and_cover_crop(iiif_url: str) -> bytes:
    """
    Fetches the artwork sized so both dimensions cover the Frame's
    3840x2160 canvas, then center-crops to exactly 3840x2160 so it
    fills the screen edge to edge with no letterboxing. Returns JPEG
    bytes ready to upload.
    """
    src_w, src_h = _get_image_dimensions(iiif_url)

    scale = max(TARGET_W / src_w, TARGET_H / src_h)
    req_w = max(TARGET_W, math.ceil(src_w * scale))

    # "w," requests that width, letting IIIF compute height to preserve
    # aspect ratio - guarantees height >= TARGET_H too, given the scale
    # factor above.
    image_url = f"{iiif_url}/full/{req_w},/0/default.jpg"
    r = requests.get(image_url, timeout=60)
    r.raise_for_status()
    img = Image.open(io.BytesIO(r.content)).convert("RGB")

    # Guard against any rounding shortfall before cropping.
    if img.width < TARGET_W or img.height < TARGET_H:
        up_scale = max(TARGET_W / img.width, TARGET_H / img.height)
        img = img.resize(
            (math.ceil(img.width * up_scale), math.ceil(img.height * up_scale)),
            Image.LANCZOS,
        )

    left = (img.width - TARGET_W) // 2
    top = (img.height - TARGET_H) // 2
    cropped = img.crop((left, top, left + TARGET_W, top + TARGET_H))

    buf = io.BytesIO()
    cropped.save(buf, format="JPEG", quality=92)
    return buf.getvalue()