Claude finished the response
Refactoring main.py with discovery fallback logic

Good news — since GFiber uses Google's Wifi/Nest mesh tech, DHCP reservation lives in the Google Home app, not a web router page. But I noticed something while researching: DHCP reservations on Google/Nest mesh routers have a known flakiness issue — reservations sometimes don't "stick" through router reboots or device swaps. So let me give you both the manual steps and a more bulletproof fallback: auto-discovery, so the script finds the TV even if its IP changes.

Manual reservation (Google Home app):

    Open the Google Home app
    Tap Home → Wifi → Network settings → Advanced networking
    Tap DHCP IP reservations → Add IP reservations
    Select your Frame TV from the device list, enter an IP (e.g. 192.168.1.50), tap Save

If the Frame TV doesn't show up in the device list yet, make sure it's powered on and connected to Wi-Fi first, then check again.

Better fix: I'll make the script find the TV automatically instead of relying on a fixed IP.
Architected IP resolution strategy with discovery fallback and caching

Now update the config template so tv_ip is optional and update the README to explain the new fallback behavior.
Edited 3 files

Now let's sanity-check the updated main.py still parses correctly.
Ran 2 commands, read a file

You can probably skip the fixed-IP hassle entirely now — tv_ip in config.json is optional, and main.py will find the TV automatically each run. Try python3 discover_tv.py on its own first to confirm it finds your TV before moving on to the next setup step.
Readme
Document · MD 
Discover tv
PY 
Main
PY 
Config.example
Code · JSON 

ModuleNotFoundError: No module named 'pandas'

This means the pip install -r requirements.txt step either wasn't run yet, or installed into a different Python than the one you're running the script with.

Try this, in the project folder:
No-op, just illustrating commands in text response

1. Confirm which python you're using and install with the matching pip:
bash

python3 -m pip install -r requirements.txt

Using python3 -m pip (rather than a bare pip) guarantees the install goes into the same Python that python3 main.py will use — mismatches between multiple installed Pythons (e.g. system Python vs. Homebrew vs. a pyenv version) are the most common cause of this error.

2. If you're on macOS and it still fails, you may need pip3 explicitly:
bash

pip3 install -r requirements.txt

3. If you want a cleaner, isolated setup (recommended, avoids this whole class of problem):
bash

cd nga_frame_art
python3 -m venv venv
source venv/bin/activate      # on Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py --build-catalog

With a venv active, python and pip both point at the same isolated environment, so there's no ambiguity. Just remember to run source venv/bin/activate again each time you open a new terminal to test manually — though for the scheduled launchd/cron job, you'll want to point directly at venv/bin/python3 in the job definition so it doesn't depend on activation.

Let me know what python3 -m pip install -r requirements.txt outputs if it still doesn't work — the specific error will tell us more.

python3 worked. now how about:

nga_catalog.py", line 118, in build_catalog
    raise ValueError(
ValueError: Matched artworks but none had a published image available (some NGA records don't have open-access images).

Devised diagnostic approach to debug missing open-access images

That error means the object IDs you listed exist in NGA's catalog, but none of them have an image flagged openaccess = 1 — NGA restricts open-access to works actually in the public domain (openaccess=0 is often for images still under rights, e.g. more recent works, even if the object record itself is public data).

Let's find out exactly which IDs are the problem:
Created a file, ran a command

Works as expected. Copy it into your project folder (same directory as main.py/cache/):
Ran a command, read a file

Run it against the exact object IDs you put in config.json:
bash

python3 check_ids.py <id1> <id2> <id3>

Each line will tell you exactly what's going on:

    NOT FOUND — the ID doesn't exist, double-check where you got it (the number at the end of an NGA art-object-page-####.html URL)
    openaccess=0 — the record exists but NGA hasn't cleared the image for open/free reuse (common for more recent works still under rights, or occasionally older ones NGA just hasn't cleared yet)
    viewtype=alternate only, no primary — the main script only accepts primary views, so these get filtered out even though an image exists

If it's openaccess=0 for some, share the titles it prints and I can help you find open-access alternatives (or nearby works by the same artist that are cleared) — pre-1923 / long-deceased-artist works are almost always open-access.
Check ids
PY 

Re-selected cached content_id: MY_F0024

Investigated cached content behavior and formulated clarification response

That's expected behavior, not an error — it means this particular artwork was already uploaded to the TV on a previous run (its content ID got cached in state.json), so instead of re-uploading the same image it just switched the TV to display it. That MY_F#### format is exactly what the Frame's Art Mode assigns to user-uploaded content (as opposed to its built-in factory art, which uses a different prefix), so that's the normal, correct ID pattern.

Did the artwork actually show up on the TV screen? That's the real confirmation it worked end to end. A couple of things worth checking:

    Is the TV in Art Mode (not just off/standby)? The ensure_art_mode() call should switch it on, but worth glancing at the screen.
    Does the piece showing match the title main.py printed just before that line?

If it displayed correctly — you're done, this run cycle works. If nothing changed on screen, let me know and we can check whether it's a connection issue vs. an art-mode state issue.

One other note for later: if you ever want to force a re-upload (e.g. you changed the matte style, or want to test the upload path again), just delete the objectid entry from state.json, or delete the whole file to reset everything.

the art is coming across letterboxed for the screen. i'd prefer it to be cropped to cover the full tv resolution. can you adjust that? then let's rewrite the section of the readme that describes the config file. the newer config file has a matte setting that's not clear to me.
Architected image resolution strategy to eliminate letterboxing through cover-crop approach

Good catch — for a proper edge-to-edge crop, the download itself needs to fetch enough resolution on both axes (not just "best fit within 3840×2160", which was sized for letterboxing and could force an upscale after cropping). Let me fix the whole pipeline, not just the crop step.
Created a file, ran a command

Now update main.py to use the new single-step function instead of the old two-step download → letterbox:
Deliberated removing unused function for code clarity

Let's test the new pipeline end to end against a real NGA image before shipping it:
Revising config documentation and clarifying matte behavior options

Confirmed the math holds for a portrait source (a tall Vermeer, say) — it fetches enough resolution on the taller axis too, so the crop never needs to upscale. Now let's update the README with the new behavior and a clearer explanation of the config file.
Strategized config documentation improvements and standardized field naming conventions

Now let's push everything to outputs:
Ran a command, read a file

Two changes:

Cropping: image_utils.py now fetches each image at whatever resolution guarantees both dimensions cover 3840×2160 (checking NGA's info.json for the source size first), then center-crops to exactly fill the screen — no borders, no upscaling artifacts. Since existing pieces are already cached on the TV under old content IDs, delete state.json (or just the entries for pieces you want reprocessed) so they get re-uploaded with the new crop.

Config docs: Rewrote that section as a table, and clarified matte — it's the Frame's own decorative border option (same as what you'd pick in the on-TV menu), completely separate from the image cropping. Format is "type_color" (e.g. "modern_apricot"), or just "none" for no border at all.
Image utils
PY 
Main
PY 
Readme
Document · MD 
Config.example
Code · JSON 


Claude is AI and can make mistakes. Please double-check responses.
Main · PY
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
        piece = random.choice(catalog)
    else:
        state["index"] = (state["index"] + 1) % len(catalog)
        piece = catalog[state["index"]]
 
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