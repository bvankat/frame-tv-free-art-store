"""
Run this script on a schedule (cron / launchd / Task Scheduler) every
`rotate_hours`. Each run advances to the next artwork in your list and
pushes it to the Frame TV. Progress is remembered in state.json so it
picks up where it left off even after your laptop sleeps or restarts.

First-time setup:
  1. cp config.example.json config.json   and fill it in
  2. python main.py --build-catalog       (fetches museum data, resolves your list)
  3. python main.py                       (uploads + shows the first piece;
                                            accept the "Allow access?" popup
                                            on the TV the very first time)
"""

import hashlib
import json
import os
import random
import sys

import met_catalog
import nga_catalog
from image_utils import download_and_cover_crop, download_direct_and_cover_crop
from frame_uploader import upload_and_show, select_existing, get_art_mode
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


def piece_key(piece) -> str:
    """
    Namespaced id, e.g. "nga:165300" / "met:437545". Both museums number
    their objects from 1, so bare ids would collide between sources.
    """
    return f"{piece['source']}:{piece['objectid']}"


def load_state(path):
    if not os.path.exists(path):
        return {"index": -1, "uploaded": {}}  # piece_key -> content_id
    with open(path) as f:
        state = json.load(f)

    # Migrate pre-Met state, which was keyed by bare NGA object id, so
    # already-uploaded pieces aren't uploaded to the TV a second time.
    state["uploaded"] = {
        (k if ":" in k else f"nga:{k}"): v
        for k, v in state.get("uploaded", {}).items()
    }
    last_shown = state.get("last_shown")
    if last_shown and ":" not in last_shown:
        state["last_shown"] = f"nga:{last_shown}"
    return state


def save_state(path, state):
    with open(path, "w") as f:
        json.dump(state, f, indent=2)


def get_sources(cfg) -> dict:
    sources = cfg.get("sources")
    if not isinstance(sources, dict):
        sys.exit(
            "config.json has no 'sources' block - see the config fields table "
            "in the README for the current format."
        )
    return sources


def sources_key(sources) -> str:
    """
    Fingerprint of the sources config, so the cached catalog rebuilds
    itself whenever the wishlist changes instead of going stale.
    """
    blob = json.dumps(sources, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()


def get_catalog(cfg, force_rebuild=False):
    sources = get_sources(cfg)
    key = sources_key(sources)

    if not force_rebuild and os.path.exists(CATALOG_CACHE):
        with open(CATALOG_CACHE) as f:
            cached = json.load(f)
        # A bare list is the pre-Met format, so it counts as stale.
        if isinstance(cached, dict) and cached.get("key") == key:
            return cached["items"]
        print("Sources changed since the catalog was built - rebuilding.")

    nga = sources.get("nga") or {}
    met = sources.get("met") or {}

    catalog = nga_catalog.build_catalog(
        cfg["cache_dir"],
        artists=nga.get("artists"),
        object_ids=nga.get("object_ids"),
    )
    print(f"NGA: {len(catalog)} artworks matched.")

    met_items = met_catalog.build_catalog(
        cfg["cache_dir"], object_ids=met.get("object_ids")
    )
    print(f"Met: {len(met_items)} artworks matched.")
    catalog += met_items

    if not catalog:
        sys.exit("No artworks matched any source - check 'sources' in config.json.")

    with open(CATALOG_CACHE, "w") as f:
        json.dump({"key": key, "items": catalog}, f, indent=2)
    print(f"Catalog built: {len(catalog)} artworks total.")
    return catalog


def main():
    cfg = load_config()
    force_rebuild = "--build-catalog" in sys.argv

    catalog = get_catalog(cfg, force_rebuild=force_rebuild)
    if force_rebuild:
        return  # just building the catalog this run, no upload

    state = load_state(cfg["state_file"])
    tv_ip = resolve_tv_ip(cfg, state)

    # Only swap art when the Frame is already showing art. If the TV is being
    # watched (or is off, or unreachable), leave the screen alone and try
    # again next run - returning here also leaves the rotation position
    # untouched, so we don't burn through pieces nobody saw.
    art_mode = get_art_mode(tv_ip)
    if art_mode != "on":
        reason = "in use" if art_mode == "off" else "unreachable"
        print(f"TV is {reason} (art mode: {art_mode}) - leaving the screen alone.")
        save_state(cfg["state_file"], state)  # keeps last_tv_ip from discovery
        return

    if cfg.get("shuffle"):
        last_shown = state.get("last_shown")
        choices = [p for p in catalog if piece_key(p) != last_shown] or catalog
        piece = random.choice(choices)
    else:
        state["index"] = (state["index"] + 1) % len(catalog)
        piece = catalog[state["index"]]

    key = piece_key(piece)
    state["last_shown"] = key

    print(f"Selected: {piece['title']} ({piece.get('artist', '')}) [{piece['source']}]")

    content_id = state["uploaded"].get(key)
    if not content_id:
        if piece["source"] == "met":
            jpeg_bytes = download_direct_and_cover_crop(piece["image_url"])
        else:
            jpeg_bytes = download_and_cover_crop(piece["iiif_url"])
        content_id = upload_and_show(tv_ip, jpeg_bytes, matte=cfg.get("matte", "none"))
        state["uploaded"][key] = content_id
        print(f"Uploaded new content_id: {content_id}")
    else:
        # Already on the TV from a previous run - just switch to it.
        select_existing(tv_ip, content_id)
        print(f"Re-selected cached content_id: {content_id}")

    save_state(cfg["state_file"], state)


if __name__ == "__main__":
    main()