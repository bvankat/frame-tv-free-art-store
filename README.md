# Frame TV Free Art Store 
Rather than pay Samsung to show art on my TV, I'm going to pull free art from the web and push it to the TV on my own.

Rotates public-domain art from the National Gallery of Art and The Metropolitan Museum of Art's open-access collections onto your Frame TV's Art Mode, on a schedule.

 ## How it works
 - **National Gallery of Art** — art data & IIIF image links come from NGA's
   official open-data repo (CC0): https://github.com/NationalGalleryOfArt/opendata
 - **The Met** — pinned object IDs are resolved through the Met Collection API
   (https://metmuseum.github.io/), no key required. Only Open Access works have
   a downloadable image; those are CC0. Anything else is skipped with a note.
 - Both museums feed one shared rotation — a run picks from the combined list.
 - **Art only changes when the Frame is already in Art Mode.** If you're
   watching something (or the TV is off, or off-network), the run prints a
   line and exits without touching the screen — it doesn't even advance the
   rotation, so you don't burn through pieces nobody saw. It tries again on
   the next scheduled run.
 - Each image is scaled and center-cropped to fill the Frame's full
   3840×2160 canvas edge to edge (no letterboxing/borders from the
   image itself). If an artwork's aspect ratio is very different from
   16:9, this crops off some of the top/bottom or sides.
 - `main.py` runs **once per interval** (you schedule it) and advances to
   the next artwork in your list.
 - The Frame TV's art API only works over your local network — this must
   run on a machine on the same Wi-Fi/LAN as the TV. It won't work hosted
   on a random cloud server unless that server can reach your home network
   (e.g. via Tailscale).
 ## One-time setup
  
 1. **You likely don't need a fixed IP.** The script auto-discovers the
    Frame TV on your network each time it runs (via SSDP), so it keeps
    working even if the TV's IP changes. Only set `tv_ip` in `config.json`
    as a fallback if discovery doesn't find your TV (see below).
    If you'd still rather reserve a fixed IP (GFiber uses Google's
    Wifi/Nest mesh tech, so this lives in the Google Home app, not a
    traditional router page):
    - Open the **Google Home app** → **Home** → **Wifi** → **Network
      settings** → **Advanced networking** → **DHCP IP reservations** →
      **Add IP reservations**
    - Select the Frame TV (it must be powered on and connected first),
      assign it an IP, tap **Save**
    - Note: reservations on Google/Nest mesh routers occasionally don't
      survive a router reboot or device swap - if that happens, the
      auto-discovery fallback means the script keeps working anyway.
    - If discovery ever fails to find the TV (e.g. it's asleep or on a
      guest network), set `"tv_ip"` in `config.json` and the script will
      fall back to that.
 2. Install dependencies:
 ```bash
    pip install -r requirements.txt
 ```
  
 3. Copy the config template and fill it in:
 ```bash
    cp config.example.json config.json
 ```
  
    ### Config fields
  
    | Field | What it does |
    |---|---|
    | `tv_ip` | Optional fallback IP, only used if auto-discovery fails. Leave as `null` unless you need it. |
    | `sources` | One block per museum (`nga`, `met`), all mixed into a single rotation. Leave a list empty — or drop a whole block — to skip that source. |
    | `sources.nga.artists` | List of artist names, NGA-style: `"Lastname, Firstname"` (e.g. `"Vermeer, Johannes"`). Any artwork by a matching artist is added to the rotation. Send me your list and I'll get the exact NGA spelling. |
    | `sources.nga.object_ids` | Specific artwork IDs, if you want exact pieces instead of/alongside `artists`. Found at the end of the artwork's NGA URL: `nga.gov/collection/art-object-page-**1236**.html` → `1236`. Numbers or strings both work. |
    | `sources.met.object_ids` | Specific Met artwork IDs, at the end of the artwork's Met URL: `metmuseum.org/art/collection/search/**437545**` → `437545`. It must be an **Open Access** work (the artwork page says "Public Domain" and offers a download); anything else has no usable image and is skipped with a message when you build the catalog. There's no artist-name option for the Met — the Met's search is fuzzy enough that it pulls in unrelated works. |
    | `rotate_hours` | How often you intend to run the script (this is just documentation for you — the actual timing is controlled by whatever scheduler you set up in the next section, cron/launchd/Task Scheduler). |
    | `shuffle` | `false` = cycle through your list in order; `true` = pick a random piece each run. |
    | `matte` | The Frame TV's built-in decorative mat/frame border around the art, same as the physical mat options you'd pick in the Frame's on-TV menu. **This is unrelated to the image cropping** — cropping always fills the full screen; `matte` then optionally insets a colored border on top of that. Format is `"type_color"`, e.g. `"modern_apricot"`, `"shadowbox_black"`, `"flexible_neutral"`. Use plain `"none"` for no border at all (art fills the whole screen with nothing added). Types: `none`, `modernthin`, `modern`, `modernwide`, `flexible`, `shadowbox`, `panoramic`, `triptych`, `mix`, `squares`. Colors: `black`, `neutral`, `antique`, `warm`, `polar`, `sand`, `seafoam`, `sage`, `burgandy`, `navy`, `apricot`, `byzantine`, `lavender`, `redorange`, `skyblue`, `turquoise`. |
    | `cache_dir` | Where NGA's CSVs and the Met's object records get downloaded to. Leave as `./cache`. |
    | `state_file` | Where rotation progress is saved. Leave as `./state.json`. |
  
 4. Build the catalog (downloads NGA's CSVs and the Met's object records,
    ~one-time, cached 30 days):
 ```bash
    python main.py --build-catalog
 ```
    This will print how many artworks matched per museum — sanity check
    before continuing. You don't have to remember to re-run it: the catalog
    rebuilds itself automatically whenever you change `sources`.
  
 5. Run it once manually:
 ```bash
    python main.py
 ```
    **The very first time you connect, the TV will show an "Allow access?"
    popup** — accept it with your remote, then re-run the command.
  
 ## Scheduling it (macOS, every hour)
  
 Already installed as `~/Library/LaunchAgents/com.user.frametvart.plist`:
  
 ```xml
 <?xml version="1.0" encoding="UTF-8"?>
 <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
   "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
 <plist version="1.0">
 <dict>
   <key>Label</key><string>com.user.frametvart</string>
   <key>ProgramArguments</key>
   <array>
     <string>/Library/Frameworks/Python.framework/Versions/3.11/bin/python3</string>
     <string>main.py</string>
   </array>
   <key>WorkingDirectory</key>
   <string>/Users/ben/Documents/Apps and Code/Frame TV Art Switcher/frame-tv-free-art-store</string>
   <key>StartInterval</key><integer>3600</integer>
   <key>StandardOutPath</key><string>/tmp/frametvart.log</string>
   <key>StandardErrorPath</key><string>/tmp/frametvart.err</string>
 </dict>
 </plist>
 ```
  
 Two things that will bite you if you recreate this from scratch:
 - **Use the full path to the Python that has the dependencies.** Apple's
   `/usr/bin/python3` is 3.9 with no `samsungtvws`/`pandas`, and launchd
   doesn't read your shell's `PATH`, so a bare `python3` won't resolve to
   the one you use in Terminal.
 - **macOS Local Network permission is per-launching-process.** The first
   time launchd starts the job, macOS asks to approve running python.org's
   Python in the background, and SSDP discovery fails with
   `OSError: [Errno 65] No route to host` until local network access is
   granted (System Settings → Privacy & Security → Local Network). The
   script survives this — it falls back to `last_tv_ip` from `state.json`,
   then `tv_ip` from the config.
  
 Load / reload / test it:
 ```bash
 launchctl bootstrap gui/$UID ~/Library/LaunchAgents/com.user.frametvart.plist
 launchctl bootout   gui/$UID/com.user.frametvart     # to stop it
 launchctl kickstart -p gui/$UID/com.user.frametvart  # run once, right now
 tail -f /tmp/frametvart.log /tmp/frametvart.err
 ```
  
 `launchctl list | grep frametvart` shows the last exit status — `0` is a
 clean run, `78` means the plist paths are wrong.
  
 If your laptop is asleep when a run is due, launchd will run it on next
 wake rather than skipping it entirely.
  
 **Windows:** use Task Scheduler, trigger "every hour", action = run
 `python.exe main.py` with "start in" set to the project folder.
  
 **Linux/Raspberry Pi:** cron entry:
 ```
 0 * * * * cd /full/path/to/frame-tv-free-art-store && /usr/bin/python3 main.py >> run.log 2>&1
 ```
  
 ## How "is the TV in use?" is detected
  
 The Frame reports `PowerState: "on"` whether you're watching something *or*
 it's sitting in Art Mode, so power state alone can't tell them apart. Art
 mode status is the signal that can. Measured on a QN55LS03BAFXZA:
  
 | TV state | `PowerState` (REST) | `art.get_artmode()` |
 |---|---|---|
 | On, watching something | `"on"` | `"off"` |
 | Art Mode | `"on"` | `"on"` |
 | Off / unreachable | — | connection fails |
  
 So `frame_uploader.get_art_mode()` gates every run: anything other than
 `"on"` means leave the screen alone. Two related gotchas if you extend this:
  
 - `get_artmode()` returns the **string** `"on"`/`"off"`, so `if not
   art.get_artmode()` is always false — compare against `"on"` explicitly.
 - The REST API on port 8001 (the library's default) times out on this model;
   the working endpoint is HTTPS on 8002. Only matters if you call something
   REST-backed like `art.supported()`.
  
 ## Files
 - `nga_catalog.py` — downloads/caches NGA's open-data CSVs, resolves your
   artist/object-id list to image URLs
 - `met_catalog.py` — resolves your Met object IDs through the Met Collection
   API and caches each record under `cache/met/`
 - `image_utils.py` — downloads art at the right resolution and
   center-crops it to fill the Frame's 3840×2160 canvas edge to edge
 - `discover_tv.py` — finds the Frame TV on the network via SSDP (no fixed
   IP required)
 - `frame_uploader.py` — talks to the TV over the local websocket API, and
   checks art mode status so runs never interrupt what you're watching
 - `main.py` — the scheduled entry point
 - `config.json` — your settings (create from `config.example.json`)
 - `catalog.json` — cached resolved artwork list; rebuilds itself when
   `sources` changes (delete it to force a rebuild any other time)
 - `state.json` — remembers rotation position, already-uploaded content IDs
   (keyed `museum:objectid`), and the last IP the TV was found at
