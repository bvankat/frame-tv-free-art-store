"""
Diagnostic: checks a list of NGA object IDs against the cached CSVs and
reports exactly why each one did or didn't match (missing entirely,
found but not open-access, found but no 'primary' view, etc).

Usage: python check_ids.py 123 456 789
"""

import sys
import pandas as pd

CACHE_DIR = "./cache"


def main():
    ids = sys.argv[1:]
    if not ids:
        print("Usage: python check_ids.py <objectid> [objectid ...]")
        return

    objects = pd.read_csv(f"{CACHE_DIR}/objects.csv", usecols=["objectid", "title"], dtype=str)
    images = pd.read_csv(
        f"{CACHE_DIR}/published_images.csv",
        usecols=["depictstmsobjectid", "viewtype", "openaccess", "iiifurl"],
        dtype=str,
    ).rename(columns={"depictstmsobjectid": "objectid"})

    for oid in ids:
        obj_match = objects[objects["objectid"] == oid]
        if obj_match.empty:
            print(f"{oid}: NOT FOUND in objects.csv - check the ID is correct")
            continue

        title = obj_match.iloc[0]["title"]
        img_rows = images[images["objectid"] == oid]

        if img_rows.empty:
            print(f"{oid} ({title}): found, but NO image records at all in published_images.csv")
            continue

        statuses = []
        for _, row in img_rows.iterrows():
            statuses.append(f"viewtype={row['viewtype']} openaccess={row['openaccess']}")
        print(f"{oid} ({title}): {len(img_rows)} image row(s) -> " + "; ".join(statuses))


if __name__ == "__main__":
    main()
