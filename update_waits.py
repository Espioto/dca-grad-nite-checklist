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
try:
    page = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")
except Exception as e:
    existing = repo / "wait-times.json"
    if existing.exists():
        data = json.loads(existing.read_text(encoding="utf-8"))
        data["feedError"] = f"{type(e).__name__}: {e}"
        data["feedErrorAt"] = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
        data["message"] = "Queue Times feed temporarily unavailable; keeping last good snapshot. Disneyland app is source of truth."
        existing.write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"Queue Times unavailable; kept previous wait-times.json ({type(e).__name__}: {e})")
        raise SystemExit(0)
    print(f"Queue Times unavailable and no previous snapshot exists ({type(e).__name__}: {e})")
    raise SystemExit(0)

land = None
rides = {}
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

completed_ride_names = {"Mater's Junkyard Jamboree"}
completed_display_names = {"Mater's"}

recs = []
def add_wait(name, threshold, msg):
    r = rides.get(name)
    if r and r["is_open"] and isinstance(r.get("wait_time"), int) and r["wait_time"] <= threshold:
        recs.append({"ride": name, "wait": r["wait_time"], "status": r["status"], "land": r["land"], "message": msg, "priority": max(1, 100 - threshold)})

def add_open(name, msg, priority=78):
    r = rides.get(name)
    if r and r["is_open"] and r.get("kind") == "open_no_minutes":
        recs.append({"ride": name, "wait": None, "status": r["status"], "land": r["land"], "message": msg, "priority": priority})

def wait(name):
    r = rides.get(name)
    if not r or not r.get("is_open"):
        return None
    return r.get("wait_time")

def open_sr(name):
    r = rides.get(name)
    return bool(r and r.get("is_open") and r.get("kind") == "open_no_minutes")

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
recs = [o for o in recs if o.get("ride") not in completed_ride_names]
recs = sorted(recs, key=lambda x: (-x["priority"], 999 if x["wait"] is None else x["wait"]))[:6]

ride_rules = [
    ("Radiator Springs Racers", "Radiator Springs Racers", 60, "Must-do at night", "Worth it together if ≤60, especially after dark."),
    ("Radiator Single Rider", "Radiator Springs Racers Single Rider", None, "Split if group is down", "Single Rider is marked open; use it if everyone is okay splitting."),
    ("Guardians", "Guardians of the Galaxy - Mission: BREAKOUT!", 55, "Top hype ride", "Recommended when ≤55; go immediately if ≤45."),
    ("WEB Slingers", "WEB SLINGERS: A Spider-Man Adventure", 40, "Good bonus ride", "Recommended at ≤40; skip long waits because bigger rides matter more."),
    ("WEB Single Rider", "WEB SLINGERS: A Spider-Man Adventure Single Rider", None, "Quick add-on", "Single Rider is marked open; good if nearby and willing to split."),
    ("Incredicoaster", "Incredicoaster", 35, "High value", "Recommended at ≤35; great at night or as a reride."),
    ("Incredicoaster Single Rider", "Incredicoaster Single Rider", None, "Best reride cheat", "Single Rider is marked open; strong if the group can split."),
    ("Soarin'", "Soarin' Over California", 35, "Sit-down reset", "Recommended at ≤35 when people need a calmer ride."),
    ("Monsters Inc.", "Monsters, Inc. Mike & Sulley to the Rescue!", 15, "Low-effort indoor", "Recommended at ≤15 as a quick indoor reset."),
    ("Toy Story Mania", "Toy Story Midway Mania!", 35, "Fun group competition", "Recommended at ≤35; fun but not worth a huge wait."),
    ("Pixar Pal-A-Round", "Pixar Pal-A-Round - Non-Swinging", 25, "Photo/view ride", "Recommended at ≤25 if people want views; otherwise skip for thrill rides."),
    ("Mater's", "Mater's Junkyard Jamboree", 20, "Cars Land filler", "Recommended at ≤20 as quick filler, but not a priority."),
    ("Little Mermaid", "The Little Mermaid - Ariel's Undersea Adventure", 15, "AC reset", "Recommended at ≤15 if tired or hot; otherwise only filler."),
    ("Grizzly River Run", "Grizzly River Run", 25, "Only if okay wet", "Recommended only if short and everyone accepts getting wet."),
]

def decision_for(display, ride_name, threshold, priority_note, good_why):
    r = rides.get(ride_name)
    completed = ride_name in completed_ride_names or display in completed_display_names
    base = {"display": display, "ride": ride_name, "priorityNote": priority_note, "completed": completed}
    if completed:
        return {**base, "status": "Done", "wait": None, "isOpen": True, "recommended": False, "why": "Already completed — no need to route here again unless the group wants a reride.", "sort": 1000}
    if not r:
        return {**base, "status": "Unknown", "wait": None, "isOpen": False, "recommended": False, "why": "No live status found. Check the Disneyland app before walking over.", "sort": 90}
    status = r.get("status", "Unknown")
    wait_time = r.get("wait_time")
    is_open = bool(r.get("is_open"))
    if not is_open:
        return {**base, "status": status, "wait": wait_time, "isOpen": False, "recommended": False, "why": "Closed right now — do not route here.", "sort": 95}
    if r.get("kind") == "open_no_minutes":
        return {**base, "status": status, "wait": None, "isOpen": True, "recommended": True, "why": good_why, "sort": 5}
    if isinstance(wait_time, int) and threshold is not None:
        if wait_time <= threshold:
            return {**base, "status": status, "wait": wait_time, "isOpen": True, "recommended": True, "why": good_why, "sort": wait_time}
        over = wait_time - threshold
        return {**base, "status": status, "wait": wait_time, "isOpen": True, "recommended": False, "why": f"Not worth it yet: {wait_time} min is about {over} min over the target threshold ({threshold}). Recheck later.", "sort": 50 + wait_time}
    return {**base, "status": status, "wait": wait_time, "isOpen": True, "recommended": False, "why": "Open, but no posted minutes. Check Disneyland app / use only if nearby.", "sort": 70}

ride_decisions = [decision_for(*rule) for rule in ride_rules]
ride_decisions = sorted(ride_decisions, key=lambda d: (not d["recommended"], d["sort"], d["display"]))

now = datetime.datetime.now().astimezone()
mins = now.hour * 60 + now.minute

def label(name):
    r = rides.get(name)
    if not r:
        return "unknown"
    return r.get("status", "unknown")

def best_filler():
    candidates = [
        ("Incredicoaster", wait("Incredicoaster"), 30),
        ("Guardians", wait("Guardians of the Galaxy - Mission: BREAKOUT!"), 45),
        ("WEB Slingers", wait("WEB SLINGERS: A Spider-Man Adventure"), 40),
        ("Mater's", wait("Mater's Junkyard Jamboree"), 20),
        ("Little Mermaid", wait("The Little Mermaid - Ariel's Undersea Adventure"), 15),
        ("Soarin'", wait("Soarin' Over California") or wait("Soarin' Around the World"), 35),
    ]
    completed_filler_names = {"Mater's"}
    good = [(n,w,t) for n,w,t in candidates if n not in completed_filler_names and isinstance(w,int) and w <= t]
    if good:
        n,w,t = sorted(good, key=lambda x: x[1])[0]
        return f"Hit {n} now ({w} min)."
    if open_sr("Radiator Springs Racers Single Rider"):
        return "Radiator Single Rider is open if you’re cool splitting."
    if open_sr("Incredicoaster Single Rider"):
        return "Incredicoaster Single Rider is open if you’re cool splitting."
    return "Follow the printed block and avoid any giant standby line."

if mins < 15*60+30:
    phase = "2:30–3:30 · Din Tai Fung now"
    action = "Eat, hydrate, bathroom, and charge phones — then head back into DCA as soon as the group is done."
    why = "Early dinner replaces the old 5–6:45 waitlist block and frees up prime afternoon ride time."
elif mins < 17*60:
    phase = "3:30–5:00 · post-dinner quick wins"
    action = best_filler()
    why = "Dinner is already handled, so clear efficient rides while normal guests are still spread out."
elif mins < 18*60+30:
    phase = "5:00–6:30 · Pixar Pier / efficient ride loop"
    action = best_filler()
    why = "This used to be dinner time; now it is bonus park time for Incredicoaster, Toy Story, Soarin, or short fillers."
elif mins < 20*60:
    phase = "6:30–8:00 · golden hour + Cars Land setup"
    action = best_filler()
    why = "Use photos and medium rides, but avoid anything that risks the 8PM reset before Grad Nite."
elif mins < 21*60:
    phase = "8:00–9:00 · reset before Grad Nite"
    action = "Bathroom, water, charge phones, hoodie, regroup near Cars Land unless waits scream otherwise."
    why = "This hour is about positioning, not squeezing in a risky long line."
elif mins < 22*60:
    phase = "9:00–10:00 · Grad Nite opener"
    rw = wait("Radiator Springs Racers")
    gw = wait("Guardians of the Galaxy - Mission: BREAKOUT!")
    if isinstance(rw,int) and rw <= 60:
        action = f"Go Radiator Springs Racers together ({rw} min)."
    elif open_sr("Radiator Springs Racers Single Rider"):
        action = "Radiator Single Rider is open — use it if the group accepts splitting, otherwise pivot."
    elif isinstance(gw,int) and gw <= 45:
        action = f"Pivot to Guardians ({gw} min), then come back to Cars Land."
    else:
        action = "Start Cars Land photos/Mater’s filler and watch for Radiator or Guardians to drop."
    why = "Radiator at night is the top target, but not at any cost."
elif mins < 23*60+15:
    phase = "10:00–11:15 · Avengers Campus"
    gw = wait("Guardians of the Galaxy - Mission: BREAKOUT!")
    ww = wait("WEB SLINGERS: A Spider-Man Adventure")
    if isinstance(gw,int) and gw <= 55:
        action = f"Go Guardians now ({gw} min)."
    elif isinstance(ww,int) and ww <= 40:
        action = f"WEB Slingers is reasonable ({ww} min); use it as the bonus."
    else:
        action = "Do one Grad Nite party/photo moment, then recheck Guardians."
    why = "This is the hype block; Guardians is worth it when it drops."
elif mins < 24*60+30:
    phase = "11:15–12:30 · Pixar Pier night lap"
    iw = wait("Incredicoaster")
    if isinstance(iw,int) and iw <= 35:
        action = f"Go Incredicoaster now ({iw} min)."
    elif open_sr("Incredicoaster Single Rider"):
        action = "Incredicoaster Single Rider is open — great reride if splitting is okay."
    else:
        action = "Get water/snack/photo, then choose the shortest elite ride."
    why = "Night Incredicoaster is high value, but avoid a late-night stall."
else:
    phase = "12:30–2:00 · rerides + exit"
    action = best_filler()
    why = "Final window: shortest elite reride wins, but don’t miss meetup/exit."

schedule = {
    "phase": phase,
    "action": action,
    "why": why,
    "fingerprint": re.sub(r"\s+", " ", phase + "|" + action).strip(),
    "checkedAtLocal": now.isoformat(timespec="seconds"),
    "keyWaits": {
        "Radiator": label("Radiator Springs Racers"),
        "Radiator Single Rider": label("Radiator Springs Racers Single Rider"),
        "Guardians": label("Guardians of the Galaxy - Mission: BREAKOUT!"),
        "Incredicoaster": label("Incredicoaster"),
        "Incredicoaster Single Rider": label("Incredicoaster Single Rider"),
        "WEB Slingers": label("WEB SLINGERS: A Spider-Man Adventure"),
    }
}

wait_json = {
    "updatedAt": now.isoformat(timespec="seconds"),
    "source": URL,
    "status": "live_queue_times_html",
    "message": "Live public Queue Times page parsed. Disneyland app still wins if it disagrees.",
    "schedule": schedule,
    "opportunities": recs,
    "rideDecisions": ride_decisions,
    "completedRides": sorted(completed_ride_names),
    "rides": [rides[n] for n in priority_names if n in rides],
}
(repo / "wait-times.json").write_text(json.dumps(wait_json, indent=2), encoding="utf-8")
print("Updated wait-times.json from public Queue Times page")
print(f"SCHEDULE: {phase} — {action}")
for n in ["Radiator Springs Racers", "Radiator Springs Racers Single Rider", "Guardians of the Galaxy - Mission: BREAKOUT!", "WEB SLINGERS: A Spider-Man Adventure", "Incredicoaster", "Incredicoaster Single Rider"]:
    if n in rides:
        r = rides[n]
        print(f"{n}: {r['status']} ({r['land']})")
for o in recs:
    label_text = f"{o['wait']} min" if o.get("wait") is not None else o.get("status", "Open")
    print(f"OPPORTUNITY: {o['ride']} {label_text} — {o['message']}")
