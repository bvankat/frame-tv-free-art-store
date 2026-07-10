"""
Resolves a wishlist of artists / object IDs into NGA IIIF image URLs,
using the National Gallery of Art's official open-data CSVs
(https://github.com/NationalGalleryOfArt/opendata), released CC0.

Docs for the schema: opendata/documentation/Data Dictionary.txt
"""

import os
import json
import time
import requests
import pandas as pd

RAW_BASE = "https://raw.githubusercontent.com/NationalGalleryOfArt/opendata/main/data/"

FILES = [
    "objects.csv",
    "objects_constituents.csv",
    "constituents.csv",
    "published_images.csv",
]

CACHE_MAX_AGE_DAYS = 30


def _download_if_needed(cache_dir: str):
    os.makedirs(cache_dir, exist_ok=True)
    for fname in FILES:
        path = os.path.join(cache_dir, fname)
        if os.path.exists(path):
            age_days = (time.time() - os.path.getmtime(path)) / 86400
            if age_days < CACHE_MAX_AGE_DAYS:
                continue
        print(f"Downloading {fname} from NGA open-data repo...")
        r = requests.get(RAW_BASE + fname, timeout=120)
        r.raise_for_status()
        with open(path, "wb") as f:
            f.write(r.content)


def build_catalog(cache_dir: str, artists=None, object_ids=None) -> list[dict]:
    """
    Returns a list of dicts: {objectid, title, artist, iiif_url}
    matching the requested artists (substring match on display name,
    case-insensitive) and/or explicit object_ids.
    """
    _download_if_needed(cache_dir)
    artists = artists or []
    object_ids = set(str(i) for i in (object_ids or []))

    objects = pd.read_csv(
        os.path.join(cache_dir, "objects.csv"),
        usecols=["objectid", "title", "attribution"],
        dtype=str,
    )
    images = pd.read_csv(
        os.path.join(cache_dir, "published_images.csv"),
        usecols=["depictstmsobjectid", "iiifurl", "viewtype", "openaccess"],
        dtype=str,
    )
    images = images.rename(columns={"depictstmsobjectid": "objectid"})
    images = images[
        (images["viewtype"] == "primary") & (images["openaccess"] == "1")
    ]

    wanted_object_ids = set(object_ids)

    if artists:
        constituents = pd.read_csv(
            os.path.join(cache_dir, "constituents.csv"),
            usecols=["constituentid", "preferreddisplayname"],
            dtype=str,
        )
        needles = [a.lower() for a in artists]
        matched_constituents = constituents[
            constituents["preferreddisplayname"]
            .fillna("")
            .str.lower()
            .apply(lambda name: any(n in name for n in needles))
        ]["constituentid"]

        obj_constituents = pd.read_csv(
            os.path.join(cache_dir, "objects_constituents.csv"),
            usecols=["objectid", "constituentid", "roletype"],
            dtype=str,
        )
        matched = obj_constituents[
            obj_constituents["constituentid"].isin(matched_constituents)
            & (obj_constituents["roletype"].fillna("").str.lower() == "artist")
        ]
        wanted_object_ids |= set(matched["objectid"])

    if not wanted_object_ids:
        raise ValueError(
            "No matching artworks found. Check artist spelling "
            "(NGA uses 'Lastname, Firstname') or provide object_ids directly."
        )

    objects = objects[objects["objectid"].isin(wanted_object_ids)]
    merged = objects.merge(images, on="objectid", how="inner")
    merged = merged.drop_duplicates(subset="objectid")

    catalog = []
    for _, row in merged.iterrows():
        if not isinstance(row["iiifurl"], str) or not row["iiifurl"]:
            continue
        catalog.append(
            {
                "objectid": row["objectid"],
                "title": row["title"],
                "artist": row.get("attribution", ""),
                "iiif_url": row["iiifurl"],
            }
        )

    if not catalog:
        raise ValueError(
            "Matched artworks but none had a published image available "
            "(some NGA records don't have open-access images)."
        )

    return catalog


def full_res_jpg_url(iiif_url: str, max_w=3840, max_h=2160) -> str:
    """
    Build an IIIF Image API request that returns the image best-fit
    within max_w x max_h (preserves aspect ratio), as JPEG.
    """
    return f"{iiif_url}/full/!{max_w},{max_h}/0/default.jpg"


if __name__ == "__main__":
    # quick manual test
    cat = build_catalog("./cache", artists=["Vermeer, Johannes"])
    print(json.dumps(cat[:3], indent=2))
