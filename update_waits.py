#!/usr/bin/env python3
"""Write a safe ride-wait sidecar for the DCA Grad Nite site.

Queue Times was disagreeing with the official Disneyland app during the event
(e.g. Radiator Springs Racers showed 85 min in-app while the third-party feed
suggested misleading single-rider/low waits). For same-day park strategy, the
Disneyland app is authoritative, so this intentionally disables automated ride
recommendations rather than publishing wrong numbers.
"""
import datetime
import json
from pathlib import Path

repo = Path(__file__).resolve().parent
wait_json = {
    "updatedAt": datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(timespec="seconds"),
    "source": "Official Disneyland app required; third-party queue feed disabled after mismatch",
    "status": "manual_app_check_required",
    "message": "Use the Disneyland app as the source of truth for posted waits. Send Hermes a screenshot or wait list and Hermes will call the best pivot.",
    "opportunities": [],
    "rides": [],
    "rules": [
        "Radiator Springs Racers: if 85 min, do not burn prime afternoon unless the group really wants it; save for night or use single rider only if the app itself shows it is available/short.",
        "Guardians: good if roughly <=45 min.",
        "Incredicoaster: good if roughly <=25–30 min, or single rider if the group is cool splitting.",
        "WEB Slingers: good if roughly <=35–40 min.",
        "Monsters Inc: good filler if roughly <=15 min.",
        "Soarin: good sit-down reset if roughly <=30–35 min."
    ]
}
(repo / "wait-times.json").write_text(json.dumps(wait_json, indent=2), encoding="utf-8")
print("Updated wait-times.json in manual-app-check mode")
