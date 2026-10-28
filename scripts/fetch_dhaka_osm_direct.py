import urllib.request
import xml.etree.ElementTree as ET
import json
import time
import os
import numpy as np

# Zones across Dhaka: (min_lon, min_lat, max_lon, max_lat)
zones = [
    ("Dhanmondi", 90.368, 23.740, 90.378, 23.752),
    ("Gulshan", 90.412, 23.785, 90.422, 23.798),
    ("Banani", 90.395, 23.788, 90.405, 23.800),
    ("Uttara", 90.390, 23.865, 90.400, 23.878),
    ("Mirpur", 90.358, 23.800, 90.368, 23.812),
    ("Lalmatia_Mohammadpur", 90.362, 23.755, 90.372, 23.768),
]

all_buildings = []
building_ids = set()

headers = {'User-Agent': 'DhakaUrbanIoTResearch/1.0 (academic research; iot-mesh)'}

for zone_name, min_lon, min_lat, max_lon, max_lat in zones:
    print(f"Fetching OSM data for {zone_name} [{min_lon}, {min_lat}, {max_lon}, {max_lat}]...")
    url = f"https://api.openstreetmap.org/api/0.6/map?bbox={min_lon:.4f},{min_lat:.4f},{max_lon:.4f},{max_lat:.4f}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            xml_data = resp.read()
        root = ET.fromstring(xml_data)
        
        # Build node coordinate dictionary
        node_coords = {}
        for node in root.findall('node'):
            nid = node.attrib.get('id')
            lat = float(node.attrib.get('lat'))
            lon = float(node.attrib.get('lon'))
            node_coords[nid] = (lat, lon)
            
        print(f"  Parsed {len(node_coords)} nodes in {zone_name}.")
        
        # Find ways tagged as building or residential
        zone_buildings = 0
        for way in root.findall('way'):
            wid = way.attrib.get('id')
            is_building = False
            b_type = "building"
            for tag in way.findall('tag'):
                k = tag.attrib.get('k')
                v = tag.attrib.get('v')
                if k == 'building':
                    is_building = True
                    b_type = v
                elif k in ('residential', 'landuse') and v == 'residential':
                    is_building = True
                    
            if is_building and wid not in building_ids:
                # Calculate centroid
                nd_refs = [nd.attrib.get('ref') for nd in way.findall('nd')]
                pts = [node_coords[ref] for ref in nd_refs if ref in node_coords]
                if len(pts) >= 3:
                    avg_lat = float(np.mean([p[0] for p in pts]))
                    avg_lon = float(np.mean([p[1] for p in pts]))
                    building_ids.add(wid)
                    all_buildings.append({
                        "id": wid,
                        "zone": zone_name,
                        "type": b_type,
                        "lat": avg_lat,
                        "lon": avg_lon
                    })
                    zone_buildings += 1
                    
        print(f"  Extracted {zone_buildings} real buildings in {zone_name}. (Total: {len(all_buildings)})")
    except Exception as e:
        print(f"  Error fetching {zone_name}: {e}")
    time.sleep(1)

print(f"\nTotal real buildings extracted across Dhaka: {len(all_buildings)}")

os.makedirs("data", exist_ok=True)
with open("data/dhaka_real_1000_buildings.json", "w", encoding="utf-8") as f:
    json.dump(all_buildings, f, indent=2)

print("Saved to data/dhaka_real_1000_buildings.json")
