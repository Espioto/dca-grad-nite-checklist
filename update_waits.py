#!/usr/bin/env python3
import json, urllib.request, datetime
from pathlib import Path

repo = Path(__file__).resolve().parent
req = urllib.request.Request('https://queue-times.com/parks/17/queue_times.json', headers={'User-Agent':'Mozilla/5.0'})
data = json.load(urllib.request.urlopen(req, timeout=15))
rides = {}
for land in data['lands']:
    for r in land['rides']:
        rides[r['name']] = dict(r, land=land['name'])

priority_names = [
    'Radiator Springs Racers','Radiator Springs Racers Single Rider','Guardians of the Galaxy - Mission: BREAKOUT!',
    'WEB SLINGERS: A Spider-Man Adventure','WEB SLINGERS: A Spider-Man Adventure Single Rider','Incredicoaster','Incredicoaster Single Rider',
    "Soarin' Over California",'Monsters, Inc. Mike & Sulley to the Rescue!',"Mater's Junkyard Jamboree",
    "The Little Mermaid - Ariel's Undersea Adventure",'Pixar Pal-A-Round – Non-Swinging','Grizzly River Run'
]

recs = []
def add(name, threshold, msg):
    r = rides.get(name)
    if r and r.get('is_open') and int(r.get('wait_time', 999)) <= threshold:
        recs.append({'ride': name, 'wait': r['wait_time'], 'land': r['land'], 'message': msg, 'priority': max(1, 100-threshold)})

add('Radiator Springs Racers', 45, 'Go now if the group wants to stay together; this is a great Radiator window.')
add('Radiator Springs Racers Single Rider', 10, 'Single rider Radiator is basically free — do it if splitting is okay.')
add('Guardians of the Galaxy - Mission: BREAKOUT!', 45, 'Guardians under 45 is worth jumping on.')
add('WEB SLINGERS: A Spider-Man Adventure', 35, 'WEB Slingers is worth it at this wait; otherwise skip huge lines.')
add('WEB SLINGERS: A Spider-Man Adventure Single Rider', 10, 'WEB Slingers single rider is open/short — good quick add-on.')
add('Incredicoaster', 25, 'Incredicoaster is short enough to hit or reride.')
add('Incredicoaster Single Rider', 10, 'Incredicoaster single rider is basically free.')
add("Soarin' Over California", 30, 'Soarin is a good sit-down reset at this wait.')
add('Monsters, Inc. Mike & Sulley to the Rescue!', 15, 'Monsters Inc. is a good warmup/low-energy ride right now.')
add("Mater's Junkyard Jamboree", 20, 'Mater’s is short and fun — good Cars Land filler.')
recs = sorted(recs, key=lambda x: (-x['priority'], x['wait']))[:5]

wait_json = {
    'updatedAt': datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(timespec='seconds'),
    'source': 'queue-times.com park 17 Disney California Adventure',
    'opportunities': recs,
    'rides': [
        {'name': n, 'land': rides[n]['land'], 'is_open': rides[n]['is_open'], 'wait_time': rides[n]['wait_time'], 'last_updated': rides[n]['last_updated']}
        for n in priority_names if n in rides
    ]
}
(repo / 'wait-times.json').write_text(json.dumps(wait_json, indent=2), encoding='utf-8')
print('Updated wait-times.json')
for o in recs:
    print(f"OPPORTUNITY: {o['ride']} {o['wait']} min — {o['message']}")
