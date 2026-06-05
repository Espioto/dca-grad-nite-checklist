#!/usr/bin/env python3
import datetime
import html
import json
import re
import urllib.request
from pathlib import Path

repo = Path(__file__).resolve().parent
URL = "https://queue-times.com/en-US/parks/17/queue_times"
req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0", "Accept": "text/html,*/*"})
page = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")

land = None
rides = {}
# The public page groups rides in <nav> panels. We parse in page order so each ride inherits the current land heading.
pattern = re.compile(
    r"<h2 class='has-text-weight-bold'>\s*(?P<land>.*?)\s*</h2>"
    r"|<a class=\"panel-block\" href=\"/en-US/parks/17/rides/(?P<id>\d+)\">\s*"
    r"<span class='has-text-weight-normal'>(?P<name>.*?)</span>\s*"
    r"<span class='(?P<class>[^']*)'[^>]*>\s*(?P<status>.*?)\s*</span>",
    re.S,
)
for m in pattern.finditer(page):
    if m.group("land") is not None:
        land = html.unescape(re.sub(r"<.*?>", "", m.group("land"))).strip()
        continue
    name = html.unescape(re.sub(r"<.*?>", "", m.group("name"))).strip()
    status_text = html.unescape(re.sub(r"<.*?>", "", m.group("status"))).strip()
    status_norm = re.sub(r"\s+", " ", status_text)
    wait = None
    is_open = True
    kind = "posted"
    if re.search(r"closed", status_norm, re.I):
        is_open = False
        kind = "closed"
    elif re.search(r"open", status_norm, re.I):
        wait = None
        kind = "open_no_minutes"
    else:
        mm = re.search(r"(\d+)\s*mins?", status_norm, re.I)
        if mm:
            wait = int(mm.group(1))
    rides[name] = {
        "id": m.group("id"),
        "name": name,
        "land": land or "Unknown",
        "is_open": is_open,
        "status": status_norm,
        "wait_time": wait,
        "kind": kind,
    }

priority_names = [
    "Radiator Springs Racers",
    "Radiator Springs Racers Single Rider",
    "Guardians of the Galaxy - Mission: BREAKOUT!",
    "WEB SLINGERS: A Spider-Man Adventure",
    "WEB SLINGERS: A Spider-Man Adventure Single Rider",
    "Incredicoaster",
    "Incredicoaster Single Rider",
    "Soarin' Around the World",
    "Soarin' Over California",
    "Monsters, Inc. Mike & Sulley to the Rescue!",
    "Mater's Junkyard Jamboree",
    "The Little Mermaid - Ariel's Undersea Adventure",
    "Toy Story Midway Mania!",
    "Pixar Pal-A-Round - Non-Swinging",
    "Grizzly River Run",
]

recs = []
def add_wait(name, threshold, msg):
    r = rides.get(name)
    if r and r["is_open"] and isinstance(r.get("wait_time"), int) and r["wait_time"] <= threshold:
        recs.append({"ride": name, "wait": r["wait_time"], "status": r["status"], "land": r["land"], "message": msg, "priority": max(1, 100 - threshold)})

def add_open(name, msg, priority=78):
    r = rides.get(name)
    if r and r["is_open"] and r.get("kind") == "open_no_minutes":
        recs.append({"ride": name, "wait": None, "status": r["status"], "land": r["land"], "message": msg, "priority": priority})

add_wait("Radiator Springs Racers", 45, "Great posted Radiator window for the whole group.")
add_open("Radiator Springs Racers Single Rider", "Single Rider is marked Open — only use if splitting is okay; it is not a guaranteed 0-minute wait.", 82)
add_wait("Guardians of the Galaxy - Mission: BREAKOUT!", 45, "Guardians at/under 45 is worth jumping on.")
add_wait("WEB SLINGERS: A Spider-Man Adventure", 40, "WEB Slingers is worth it at this wait; skip giant lines.")
add_open("WEB SLINGERS: A Spider-Man Adventure Single Rider", "WEB Slingers Single Rider is marked Open — good quick add-on if nearby.", 78)
add_wait("Incredicoaster", 30, "Incredicoaster is short enough to hit or reride.")
add_open("Incredicoaster Single Rider", "Incredicoaster Single Rider is marked Open — strong option if the group will split.", 82)
add_wait("Soarin' Around the World", 35, "Soarin is a good sit-down reset at this wait.")
add_wait("Soarin' Over California", 35, "Soarin is a good sit-down reset at this wait.")
add_wait("Monsters, Inc. Mike & Sulley to the Rescue!", 15, "Monsters Inc. is a good warmup/low-energy ride right now.")
add_wait("Mater's Junkyard Jamboree", 20, "Mater’s is short and fun — good Cars Land filler.")
add_wait("The Little Mermaid - Ariel's Undersea Adventure", 15, "Little Mermaid is a good AC/sit-down reset if people are tired.")
recs = sorted(recs, key=lambda x: (-x["priority"], 999 if x["wait"] is None else x["wait"]))[:6]

wait_json = {
    "updatedAt": datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(timespec="seconds"),
    "source": URL,
    "status": "live_queue_times_html",
    "message": "Live public Queue Times page parsed. Disneyland app still wins if it disagrees.",
    "opportunities": recs,
    "rides": [rides[n] for n in priority_names if n in rides],
}
(repo / "wait-times.json").write_text(json.dumps(wait_json, indent=2), encoding="utf-8")
print("Updated wait-times.json from public Queue Times page")
for n in ["Radiator Springs Racers", "Radiator Springs Racers Single Rider", "Guardians of the Galaxy - Mission: BREAKOUT!", "WEB SLINGERS: A Spider-Man Adventure", "Incredicoaster", "Incredicoaster Single Rider"]:
    if n in rides:
        r = rides[n]
        print(f"{n}: {r['status']} ({r['land']})")
for o in recs:
    label = f"{o['wait']} min" if o.get("wait") is not None else o.get("status", "Open")
    print(f"OPPORTUNITY: {o['ride']} {label} — {o['message']}")
