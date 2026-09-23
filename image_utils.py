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


def _cover_crop_to_jpeg(img: Image.Image) -> bytes:
    """
    Scales `img` up if needed so it covers the Frame's 3840x2160 canvas,
    center-crops to exactly that size so it fills the screen edge to edge
    with no letterboxing, and returns JPEG bytes ready to upload.
    """
    img = img.convert("RGB")

    if img.width < TARGET_W or img.height < TARGET_H:
        up_scale = max(TARGET_W / img.width, TARGET_H / img.height)
        # A few pixels short is invisible; only flag a real upscale.
        if up_scale > 1.05:
            print(
                f"Source is only {img.width}x{img.height} - upscaling {up_scale:.1f}x "
                f"to cover {TARGET_W}x{TARGET_H} (may look soft on the TV)."
            )
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


def download_direct_and_cover_crop(image_url: str) -> bytes:
    """
    For sources that serve a plain JPEG at a fixed resolution (The Met),
    rather than a IIIF endpoint we can ask for an exact size.
    """
    # Met originals run to ~8MB, hence the generous timeout.
    r = requests.get(image_url, timeout=120)
    r.raise_for_status()
    return _cover_crop_to_jpeg(Image.open(io.BytesIO(r.content)))


def download_and_cover_crop(iiif_url: str) -> bytes:
    """
    Fetches the artwork from a IIIF endpoint (NGA) sized so both
    dimensions cover the Frame's 3840x2160 canvas, then center-crops it
    to fill the screen. Returns JPEG bytes ready to upload.
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

    # _cover_crop_to_jpeg also guards against any rounding shortfall.
    return _cover_crop_to_jpeg(Image.open(io.BytesIO(r.content)))