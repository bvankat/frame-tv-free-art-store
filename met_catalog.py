"""
Resolves a list of Met object IDs into direct image URLs, using The
Metropolitan Museum of Art's Collection API (https://metmuseum.github.io/).

No API key required. Open Access artworks are released CC0; anything not
Open Access comes back with an empty primaryImage and is skipped.

Object IDs are the tail of the artwork's page URL:
https://www.metmuseum.org/art/collection/search/437545 -> 437545
"""

import os
import json
import time
import requests

API_BASE = "https://collectionapi.metmuseum.org/public/collection/v1/objects/"

CACHE_MAX_AGE_DAYS = 30


def _fetch_object(cache_dir: str, objectid: str) -> dict:
    """
    Returns the Met's JSON record for one object, cached on disk so
    rebuilding the catalog doesn't re-hit the API for artworks we've
    already looked up.
    """
    met_cache = os.path.join(cache_dir, "met")
    os.makedirs(met_cache, exist_ok=True)
    path = os.path.join(met_cache, f"{objectid}.json")

    if os.path.exists(path):
        age_days = (time.time() - os.path.getmtime(path)) / 86400
        if age_days < CACHE_MAX_AGE_DAYS:
            with open(path) as f:
                return json.load(f)

    print(f"Fetching Met object {objectid}...")
    r = requests.get(API_BASE + str(objectid), timeout=30)
    r.raise_for_status()
    data = r.json()
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return data


def build_catalog(cache_dir: str, object_ids=None) -> list[dict]:
    """
    Returns a list of dicts: {source, objectid, title, artist, image_url}
    for each requested object that has an Open Access image.
    """
    object_ids = [str(i) for i in (object_ids or [])]
    if not object_ids:
        return []

    catalog = []
    for objectid in object_ids:
        try:
            data = _fetch_object(cache_dir, objectid)
        except requests.HTTPError as e:
            print(f"  Skipping Met {objectid}: {e}")
            continue

        image_url = data.get("primaryImage") or ""
        if not image_url:
            reason = (
                "not Open Access"
                if not data.get("isPublicDomain")
                else "no primary image published"
            )
            print(f"  Skipping Met {objectid} ({data.get('title', '?')}): {reason}.")
            continue

        catalog.append(
            {
                "source": "met",
                "objectid": objectid,
                "title": data.get("title", ""),
                "artist": data.get("artistDisplayName", ""),
                "image_url": image_url,
            }
        )

    return catalog


if __name__ == "__main__":
    # quick manual test
    print(json.dumps(build_catalog("./cache", object_ids=[437545, 436535]), indent=2))
