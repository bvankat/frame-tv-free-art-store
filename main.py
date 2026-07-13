"""
Run this script on a schedule (cron / launchd / Task Scheduler) every
`rotate_hours`. Each run advances to the next artwork in your list and
pushes it to the Frame TV. Progress is remembered in state.json so it
picks up where it left off even after your laptop sleeps or restarts.

First-time setup:
  1. cp config.example.json config.json   and fill it in
  2. python main.py --build-catalog       (fetches NGA data, resolves your list)
  3. python main.py                       (uploads + shows the first piece;
                                            accept the "Allow access?" popup
                                            on the TV the very first time)
"""

import json
import os
import random
import sys

from nga_catalog import build_catalog
from image_utils import download_and_cover_crop
from frame_uploader import upload_and_show, ensure_art_mode
from discover_tv import discover_frame_tv

CONFIG_PATH = "config.json"
CATALOG_CACHE = "catalog.json"


def resolve_tv_ip(cfg, state) -> str:
    """
    Tries SSDP auto-discovery first (handles the TV's IP changing).
    Falls back to the last IP that worked, then to config's tv_ip.
    """
    found = discover_frame_tv()
    if found:
        if found != state.get("last_tv_ip"):
            print(f"TV found at {found}")
        state["last_tv_ip"] = found
        return found

    fallback = state.get("last_tv_ip") or cfg.get("tv_ip")
    if not fallback:
        sys.exit("Could not auto-discover the TV and no tv_ip is set in config.json.")
    print(f"Auto-discovery found nothing, using last known IP: {fallback}")
    return fallback


def load_config():
    if not os.path.exists(CONFIG_PATH):
        sys.exit("Missing config.json - copy config.example.json and fill it in first.")
    with open(CONFIG_PATH) as f:
        return json.load(f)


def load_state(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {"index": -1, "uploaded": {}}  # objectid -> content_id


def save_state(path, state):
    with open(path, "w") as f:
        json.dump(state, f, indent=2)


def get_catalog(cfg, force_rebuild=False):
    if not force_rebuild and os.path.exists(CATALOG_CACHE):
        with open(CATALOG_CACHE) as f:
            return json.load(f)
    catalog = build_catalog(
        cfg["cache_dir"], artists=cfg.get("artists"), object_ids=cfg.get("object_ids")
    )
    with open(CATALOG_CACHE, "w") as f:
        json.dump(catalog, f, indent=2)
    print(f"Catalog built: {len(catalog)} artworks matched.")
    return catalog


def main():
    cfg = load_config()
    force_rebuild = "--build-catalog" in sys.argv

    catalog = get_catalog(cfg, force_rebuild=force_rebuild)
    if force_rebuild:
        return  # just building the catalog this run, no upload

    state = load_state(cfg["state_file"])
    tv_ip = resolve_tv_ip(cfg, state)

    if cfg.get("shuffle"):
        last_shown = state.get("last_shown")
        choices = [p for p in catalog if p["objectid"] != last_shown] or catalog
        piece = random.choice(choices)
    else:
        state["index"] = (state["index"] + 1) % len(catalog)
        piece = catalog[state["index"]]

    state["last_shown"] = piece["objectid"]

    print(f"Selected: {piece['title']} ({piece.get('artist', '')})")

    content_id = state["uploaded"].get(piece["objectid"])
    if not content_id:
        jpeg_bytes = download_and_cover_crop(piece["iiif_url"])
        content_id = upload_and_show(tv_ip, jpeg_bytes, matte=cfg.get("matte", "none"))
        state["uploaded"][piece["objectid"]] = content_id
        print(f"Uploaded new content_id: {content_id}")
    else:
        # Already on the TV from a previous run - just switch to it.
        from samsungtvws import SamsungTVWS

        tv = SamsungTVWS(host=tv_ip)
        tv.art().select_image(content_id, show=True)
        tv.close()
        print(f"Re-selected cached content_id: {content_id}")

    ensure_art_mode(tv_ip)
    save_state(cfg["state_file"], state)


if __name__ == "__main__":
    main()