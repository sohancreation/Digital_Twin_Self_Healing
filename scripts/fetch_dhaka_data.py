import requests
import json
import time
import os

# Load already collected homes if available
existing_homes = []
existing_ids = set()
if os.path.exists("data/dhaka_homes_1000.json"):
    with open("data/dhaka_homes_1000.json", "r", encoding="utf-8") as f:
        existing_homes = json.load(f)
        existing_ids = {h["id"] for h in existing_homes}
    print(f"Loaded {len(existing_homes)} existing homes.")

target_areas = [
    ("Gulshan-1", 23.775, 90.410, 23.785, 90.420),
    ("Gulshan-2 North", 23.798, 90.412, 23.808, 90.422),
    ("Banani", 23.788, 90.398, 23.798, 90.408),
    ("Baridhara", 23.798, 90.420, 23.808, 90.430),
    ("Niketan", 23.772, 90.405, 23.780, 90.415),
    ("Mohakhali DOHS", 23.778, 90.388, 23.788, 90.398),
    ("Dhanmondi South", 23.738, 90.370, 23.748, 90.380),
    ("Dhanmondi Central", 23.748, 90.370, 23.758, 90.380),
    ("Lalmatia", 23.755, 90.365, 23.765, 90.375),
    ("Mohammadpur", 23.765, 90.355, 23.775, 90.365),
    ("Mirpur-1", 23.795, 90.345, 23.805, 90.355),
    ("Mirpur-10", 23.805, 90.365, 23.815, 90.375),
    ("Uttara Sector 7-10", 23.870, 90.390, 23.880, 90.400),
    ("Bashundhara R/A", 23.812, 90.425, 23.822, 90.435),
]

endpoints = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter"
]

for name, s, w, n, e in target_areas:
    if len(existing_homes) >= 1200:
        break
    print(f"Querying {name} ({s:.3f}, {w:.3f}, {n:.3f}, {e:.3f})...", flush=True)
    q = f"""[out:json][timeout:25];
(
  way["building"]({s:.4f},{w:.4f},{n:.4f},{e:.4f});
);
out center 150;
"""
    fetched = False
    for ep in endpoints:
        try:
            r = requests.post(
                ep,
                data={"data": q},
                headers={"User-Agent": "DhakaUrbanTopology/1.0 (academic; building-mesh)"},
                timeout=25
            )
            if r.status_code == 200:
                elems = r.json().get("elements", [])
                added = 0
                for el in elems:
                    eid = el.get("id")
                    c = el.get("center")
                    if eid and c and eid not in existing_ids:
                        existing_ids.add(eid)
                        existing_homes.append({
                            "id": eid,
                            "neighborhood": name,
                            "lat": c["lat"],
                            "lon": c["lon"]
                        })
                        added += 1
                print(f"  -> {name} via {ep}: found {len(elems)}, added {added} new (Total: {len(existing_homes)})", flush=True)
                fetched = True
                break
            else:
                print(f"  -> {ep} returned HTTP {r.status_code}", flush=True)
        except Exception as exc:
            print(f"  -> {ep} failed: {exc}", flush=True)
        time.sleep(1)
    time.sleep(1.5)

print(f"\nFinal count of collected Dhaka home coordinates: {len(existing_homes)}")
with open("data/dhaka_homes_1000.json", "w", encoding="utf-8") as f:
    json.dump(existing_homes, f, indent=2)
print("Updated data/dhaka_homes_1000.json successfully!")
