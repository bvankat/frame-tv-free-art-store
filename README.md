# Frame TV Free Art Store 
Rather than pay Samsung to show art on my TV, I'm going to pull free art from the web and push it to the TV on my own.

Rotates public-domain art from the National Gallery of Art's open-access collection onto your Frame TV's Art Mode, on a schedule.

 ## How it works
 - Art data & IIIF image links come from NGA's official open-data repo
   (CC0): https://github.com/NationalGalleryOfArt/opendata
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
    | `artists` | List of artist names, NGA-style: `"Lastname, Firstname"` (e.g. `"Vermeer, Johannes"`). Any artwork by a matching artist is added to the rotation. Send me your list and I'll get the exact NGA spelling. |
    | `object_ids` | Specific artwork IDs, if you want exact pieces instead of/alongside `artists`. Found at the end of the artwork's NGA URL: `nga.gov/collection/art-object-page-**1236**.html` → `1236`. Numbers or strings both work. |
    | `rotate_hours` | How often you intend to run the script (this is just documentation for you — the actual timing is controlled by whatever scheduler you set up in the next section, cron/launchd/Task Scheduler). |
    | `shuffle` | `false` = cycle through your list in order; `true` = pick a random piece each run. |
    | `matte` | The Frame TV's built-in decorative mat/frame border around the art, same as the physical mat options you'd pick in the Frame's on-TV menu. **This is unrelated to the image cropping** — cropping always fills the full screen; `matte` then optionally insets a colored border on top of that. Format is `"type_color"`, e.g. `"modern_apricot"`, `"shadowbox_black"`, `"flexible_neutral"`. Use plain `"none"` for no border at all (art fills the whole screen with nothing added). Types: `none`, `modernthin`, `modern`, `modernwide`, `flexible`, `shadowbox`, `panoramic`, `triptych`, `mix`, `squares`. Colors: `black`, `neutral`, `antique`, `warm`, `polar`, `sand`, `seafoam`, `sage`, `burgandy`, `navy`, `apricot`, `byzantine`, `lavender`, `redorange`, `skyblue`, `turquoise`. |
    | `cache_dir` | Where NGA's CSVs get downloaded to. Leave as `./cache`. |
    | `state_file` | Where rotation progress is saved. Leave as `./state.json`. |
  
 4. Build the catalog (downloads NGA's CSVs, ~one-time, cached 30 days):
 ```bash
    python main.py --build-catalog
 ```
    This will print how many artworks matched your list — sanity check
    before continuing.
  
 5. Run it once manually:
 ```bash
    python main.py
 ```
    **The very first time you connect, the TV will show an "Allow access?"
    popup** — accept it with your remote, then re-run the command.
  
 ## Scheduling it (macOS example, every 2 hours)
  
 Create `~/Library/LaunchAgents/com.user.ngaframeart.plist`:
  
 ```xml
 <?xml version="1.0" encoding="UTF-8"?>
 <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
   "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
 <plist version="1.0">
 <dict>
   <key>Label</key><string>com.user.ngaframeart</string>
   <key>ProgramArguments</key>
   <array>
     <string>/usr/bin/python3</string>
     <string>/FULL/PATH/TO/nga_frame_art/main.py</string>
   </array>
   <key>WorkingDirectory</key><string>/FULL/PATH/TO/nga_frame_art</string>
   <key>StartInterval</key><integer>7200</integer>
   <key>StandardOutPath</key><string>/tmp/ngaframeart.log</string>
   <key>StandardErrorPath</key><string>/tmp/ngaframeart.err</string>
 </dict>
 </plist>
 ```
  
 Load it:
 ```bash
 launchctl load ~/Library/LaunchAgents/com.user.ngaframeart.plist
 ```
  
 If your laptop is asleep when a run is due, launchd will run it on next
 wake rather than skipping it entirely.
  
 **Windows:** use Task Scheduler, trigger "every 2 hours", action = run
 `python.exe main.py` with "start in" set to the project folder.
  
 **Linux/Raspberry Pi:** cron entry:
 ```
 0 */2 * * * cd /full/path/to/nga_frame_art && /usr/bin/python3 main.py >> run.log 2>&1
 ```
  
 ## Files
 - `nga_catalog.py` — downloads/caches NGA's open-data CSVs, resolves your
   artist/object-id list to image URLs
 - `image_utils.py` — downloads art at the right resolution and
   center-crops it to fill the Frame's 3840×2160 canvas edge to edge
 - `discover_tv.py` — finds the Frame TV on the network via SSDP (no fixed
   IP required)
 - `frame_uploader.py` — talks to the TV over the local websocket API
 - `main.py` — the scheduled entry point
 - `config.json` — your settings (create from `config.example.json`)
 - `catalog.json` — cached resolved artwork list (delete to force rebuild)
 - `state.json` — remembers rotation position, already-uploaded content IDs,
   and the last IP the TV was found at
