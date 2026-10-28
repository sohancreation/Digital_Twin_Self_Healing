"""
Publication-Quality 1,000-Node IoT Topology Generator based on REAL Dhaka Household Geospatial Coordinates.
Extracted directly from OpenStreetMap (OSM) building footprints across major Dhaka residential districts:
- Dhanmondi
- Gulshan
- Banani
- Mirpur
- Lalmatia / Mohammadpur
- Uttara

Three-Tier Network Architecture:
- Green: Intra-district Sensor-to-Sensor mesh connections (short-range RF)
- Brown: Household-to-Gateway uplink connections
- Orange: Inter-district Gateway-to-Gateway transit backbone routes
- Blue Nodes: Household IoT Smart Sensors
- Red Nodes: District Gateway and Transit Bridge Hubs
"""

import os
import json
import numpy as np
import networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from pathlib import Path

# Publication typography
matplotlib.rcParams['font.family'] = 'serif'
matplotlib.rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif', 'Times']
matplotlib.rcParams['mathtext.fontset'] = 'cm'
matplotlib.rcParams['pdf.fonttype'] = 42
matplotlib.rcParams['ps.fonttype'] = 42

def load_and_sample_dhaka_homes(json_path="data/dhaka_real_1000_buildings.json", seed=142):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    rng = np.random.default_rng(seed)
    
    # 6 Major Dhaka residential clusters totaling exactly 1,000 homes
    zone_alloc = {
        'Dhanmondi': 240,            # Dense residential core (South-West)
        'Lalmatia_Mohammadpur': 180, # Adjacent residential zone (West)
        'Gulshan': 200,              # Diplomatic & residential hub (East)
        'Banani': 140,               # Residential / commercial neighbor (Central-East)
        'Mirpur': 140,               # Northern residential cluster (North-West)
        'Uttara': 100                # Planned satellite residential city (North)
    }
    
    selected_homes = []
    zone_indices = {}
    current_idx = 0
    
    for zone, count in zone_alloc.items():
        z_items = [d for d in data if d['zone'] == zone]
        if len(z_items) < count:
            raise ValueError(f"Zone {zone} has only {len(z_items)} items, needed {count}")
        chosen_indices = rng.choice(len(z_items), count, replace=False)
        start_idx = current_idx
        for ci in chosen_indices:
            item = z_items[ci]
            selected_homes.append({
                'node_id': current_idx,
                'osm_id': item['id'],
                'zone': zone,
                'lat': float(item['lat']),
                'lon': float(item['lon'])
            })
            current_idx += 1
        end_idx = current_idx
        zone_indices[zone] = list(range(start_idx, end_idx))
        
    print(f"Sampled exactly {len(selected_homes)} real homes across {len(zone_alloc)} Dhaka zones.")
    return selected_homes, zone_indices


def build_dhaka_iot_mesh_topology(selected_homes, zone_indices, seed=142):
    rng = np.random.default_rng(seed)
    num_nodes = len(selected_homes)
    
    # Extract coordinates (Lon as X, Lat as Y)
    raw_coords = np.array([[h['lon'], h['lat']] for h in selected_homes])
    
    # Normalize coordinates to [0, 1] range for visualization and distance calculations
    min_x, max_x = raw_coords[:, 0].min(), raw_coords[:, 0].max()
    min_y, max_y = raw_coords[:, 1].min(), raw_coords[:, 1].max()
    
    # Preserve true geographic aspect ratio
    # 1 deg lat in Dhaka is ~110.8 km, 1 deg lon is ~101.9 km (cos(23.8 deg) * 111.3)
    lat_scale = 110.8
    lon_scale = 101.9
    
    norm_x = (raw_coords[:, 0] - min_x) * lon_scale
    norm_y = (raw_coords[:, 1] - min_y) * lat_scale
    
    # Scale to canvas coordinates
    pos_scale = max(norm_x.max(), norm_y.max())
    positions = {}
    for i in range(num_nodes):
        positions[i] = np.array([norm_x[i] / pos_scale, norm_y[i] / pos_scale])
        
    # Classify Gateway / Bridge Nodes (Red):
    # In each district, pick ~15-20% high-degree, well-positioned transit hubs
    is_bridge = np.zeros(num_nodes, dtype=bool)
    zone_gateways = {}
    
    for zone, n_list in zone_indices.items():
        z_pos = np.array([positions[n] for n in n_list])
        z_center = np.mean(z_pos, axis=0)
        dists = np.linalg.norm(z_pos - z_center, axis=1)
        
        # Select central gateway hub + perimeter transit relays
        sorted_idx = np.argsort(dists)
        n_gateways = max(8, int(len(n_list) * 0.16))
        
        # Core gateways near centroid
        core_gw = [n_list[idx] for idx in sorted_idx[:n_gateways // 2]]
        # Perimeter transit relays distributed across the zone
        perim_gw = [n_list[idx] for idx in sorted_idx[n_gateways // 2:n_gateways]]
        
        selected_gw = core_gw + perim_gw
        for gw in selected_gw:
            is_bridge[gw] = True
        zone_gateways[zone] = selected_gw
        
    G = nx.Graph()
    G.add_nodes_from(range(num_nodes))
    
    # 1. Sensor-to-Sensor (Green Links): Dense local wireless mesh within each district
    for zone, n_list in zone_indices.items():
        z_sensors = [n for n in n_list if not is_bridge[n]]
        z_pos = np.array([positions[n] for n in z_sensors])
        
        for idx, u in enumerate(z_sensors):
            dists = np.linalg.norm(z_pos - z_pos[idx], axis=1)
            # Connect to 3 to 6 nearest neighboring homes within RF range
            k_mesh = rng.integers(3, 7)
            near_idx = np.argsort(dists)[1:k_mesh + 1]
            for ni in near_idx:
                # Add edge within local radio reach
                G.add_edge(u, z_sensors[ni])
                
    # 2. Sensor-to-Bridge / Household-to-Gateway (Brown Links)
    # Each gateway connects to 4-8 nearby sensor homes; each sensor attaches to nearest gateway
    for zone, n_list in zone_indices.items():
        gws = zone_gateways[zone]
        sensors = [n for n in n_list if not is_bridge[n]]
        s_pos = np.array([positions[n] for n in sensors])
        
        for gw in gws:
            dists = np.linalg.norm(s_pos - positions[gw], axis=1)
            k_att = min(len(sensors), rng.integers(4, 9))
            near_s = np.argsort(dists)[:k_att]
            for si in near_s:
                G.add_edge(gw, sensors[si])
                
        # Ensure every sensor has at least one gateway path
        for s in sensors:
            gw_dists = [np.linalg.norm(positions[s] - positions[gw]) for gw in gws]
            nearest_gw = gws[np.argmin(gw_dists)]
            G.add_edge(s, nearest_gw)
            
    # 3. Gateway-to-Gateway Backbone (Orange Links)
    # Intra-zone gateway mesh
    for zone, gws in zone_gateways.items():
        for i, gw1 in enumerate(gws):
            dists = [np.linalg.norm(positions[gw1] - positions[gw2]) for gw2 in gws]
            sorted_gw = np.argsort(dists)[1:min(4, len(gws))]
            for sgw in sorted_gw:
                G.add_edge(gw1, gws[sgw])
                
    # Inter-district Transit Backbone connecting Dhaka's metropolitan corridors:
    # Dhanmondi <-> Lalmatia/Mohammadpur (adjacent western corridor)
    # Dhanmondi <-> Banani / Gulshan (central south-north highway)
    # Lalmatia <-> Mirpur (western north corridor)
    # Banani <-> Gulshan (adjacent eastern corridor)
    # Banani <-> Mirpur (cross-central connector)
    # Gulshan <-> Uttara (eastern north expressway)
    # Mirpur <-> Uttara (western north bypass)
    district_backbone_corridors = [
        ('Dhanmondi', 'Lalmatia_Mohammadpur'),
        ('Dhanmondi', 'Banani'),
        ('Dhanmondi', 'Gulshan'),
        ('Lalmatia_Mohammadpur', 'Mirpur'),
        ('Banani', 'Gulshan'),
        ('Banani', 'Mirpur'),
        ('Gulshan', 'Uttara'),
        ('Mirpur', 'Uttara'),
    ]
    
    for z1, z2 in district_backbone_corridors:
        gw1_list = zone_gateways[z1]
        gw2_list = zone_gateways[z2]
        
        # Connect 2-4 strategic backbone trunk links between gateway sets
        n_trunks = rng.integers(2, 5)
        for _ in range(n_trunks):
            gw1 = rng.choice(gw1_list)
            dists = [np.linalg.norm(positions[gw1] - positions[gw2]) for gw2 in gw2_list]
            gw2 = gw2_list[np.argmin(dists)]
            G.add_edge(gw1, gw2)
            
    # Adjacent sensor border links where neighborhoods meet (e.g. Dhanmondi & Lalmatia, Banani & Gulshan)
    adjacent_zones = [
        ('Dhanmondi', 'Lalmatia_Mohammadpur'),
        ('Banani', 'Gulshan')
    ]
    for z1, z2 in adjacent_zones:
        s1_list = [n for n in zone_indices[z1] if not is_bridge[n]]
        s2_list = [n for n in zone_indices[z2] if not is_bridge[n]]
        for _ in range(12):
            s1 = rng.choice(s1_list)
            dists = [np.linalg.norm(positions[s1] - positions[s2]) for s2 in s2_list]
            if min(dists) < 0.20:
                s2 = s2_list[np.argmin(dists)]
                G.add_edge(s1, s2)
                
    # Ensure global connectivity
    if not nx.is_connected(G):
        comps = list(nx.connected_components(G))
        for k in range(len(comps) - 1):
            comp_a = list(comps[k])
            comp_b = list(comps[k + 1])
            min_d = float('inf')
            best = (comp_a[0], comp_b[0])
            for u in comp_a[:25]:
                for v in comp_b[:25]:
                    d = np.linalg.norm(positions[u] - positions[v])
                    if d < min_d:
                        min_d = d
                        best = (u, v)
            G.add_edge(best[0], best[1])
            
    # Classify edges
    e_s2s, e_b2b, e_s2b = [], [], []
    for u, v in G.edges():
        bu, bv = is_bridge[u], is_bridge[v]
        if not bu and not bv:
            e_s2s.append((u, v))
        elif bu and bv:
            e_b2b.append((u, v))
        else:
            e_s2b.append((u, v))
            
    sensor_count = np.sum(~is_bridge)
    bridge_count = np.sum(is_bridge)
    print(f"Constructed Dhaka IoT Topology: |V| = {G.number_of_nodes()}, |E| = {G.number_of_edges()}")
    print(f"  Sensors: {sensor_count}, Gateways/Bridges: {bridge_count}")
    print(f"  Green (Sensor-to-Sensor): {len(e_s2s)}")
    print(f"  Orange (Backbone Gateway-to-Gateway): {len(e_b2b)}")
    print(f"  Brown (Sensor-to-Gateway Uplink): {len(e_s2b)}")
    
    return G, positions, is_bridge, e_s2s, e_b2b, e_s2b, selected_homes


def render_dhaka_publication_plot(
    G, positions, is_bridge, e_s2s, e_b2b, e_s2b,
    output_png="plots/fig_1000_nodes_topology_v2_clean.png",
    output_pdf="plots/fig_1000_nodes_topology_v2_clean.pdf",
    node_labels=("Household IoT Sensor", "District Gateway / Transit Hub"),
    edge_labels=("Intra-District Mesh Link", "Inter-District Transit Backbone", "Household-to-Gateway Uplink"),
    dpi=300
):
    # Figure size with exact aspect ratio 1.302 (527pt x 405pt) matching original
    fig, ax = plt.subplots(figsize=(7.5, 5.76), dpi=dpi)
    ax.set_facecolor('white')
    fig.patch.set_facecolor('white')
    
    pos = positions
    
    # Color palette
    c_green = '#2e7d32'   # Forest Green (Mesh)
    c_orange = '#f39c12'  # Amber Orange (Backbone)
    c_brown = '#8b2500'   # Sienna Brown (Uplink)
    c_blue = '#0026e6'    # Royal Blue (Sensor Nodes)
    c_red = '#e60000'     # Crimson Red (Gateway Hubs)
    
    # 1. Green links: Sensor-to-Sensor
    for u, v in e_s2s:
        ax.plot([pos[u][0], pos[v][0]], [pos[u][1], pos[v][1]],
                color=c_green, linewidth=0.52, alpha=0.68, zorder=1)
                
    # 2. Orange links: Gateway-to-Gateway Backbone
    for u, v in e_b2b:
        ax.plot([pos[u][0], pos[v][0]], [pos[u][1], pos[v][1]],
                color=c_orange, linewidth=1.05, alpha=0.86, zorder=2)
                
    # 3. Brown links: Household-to-Gateway
    for u, v in e_s2b:
        ax.plot([pos[u][0], pos[v][0]], [pos[u][1], pos[v][1]],
                color=c_brown, linewidth=0.72, alpha=0.78, zorder=2)
                
    # Nodes
    sensor_nodes = [n for n in G.nodes() if not is_bridge[n]]
    bridge_nodes = [n for n in G.nodes() if is_bridge[n]]
    
    sx = [pos[n][0] for n in sensor_nodes]
    sy = [pos[n][1] for n in sensor_nodes]
    bx = [pos[n][0] for n in bridge_nodes]
    by = [pos[n][1] for n in bridge_nodes]
    
    ax.scatter(sx, sy, c=c_blue, s=6.5, zorder=3, edgecolors='none')
    ax.scatter(bx, by, c=c_red, s=12.0, zorder=4, edgecolors='none')
    
    # Legend
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', label=node_labels[0],
               markerfacecolor=c_blue, markersize=9.5),
        Line2D([0], [0], marker='o', color='w', label=node_labels[1],
               markerfacecolor=c_red, markersize=9.5),
        Line2D([0], [1], color=c_green, lw=2.2, label=edge_labels[0]),
        Line2D([0], [1], color=c_orange, lw=2.2, label=edge_labels[1]),
        Line2D([0], [1], color=c_brown, lw=2.2, label=edge_labels[2]),
    ]
    
    leg = ax.legend(
        handles=legend_elements,
        loc='upper left',
        bbox_to_anchor=(0.01, 0.99),
        frameon=True,
        framealpha=0.96,
        edgecolor='#64748b',
        fontsize=12.5,
        labelspacing=0.45,
        handlelength=1.6,
        handletextpad=0.6,
        borderpad=0.6
    )
    leg.get_frame().set_linewidth(1.2)
    
    ax.axis('off')
    
    all_x = [pos[n][0] for n in G.nodes()]
    all_y = [pos[n][1] for n in G.nodes()]
    x_min, x_max = min(all_x), max(all_x)
    y_min, y_max = min(all_y), max(all_y)
    dx = x_max - x_min
    dy = y_max - y_min
    
    # Provide comfortable margin on the left for the legend without obscuring nodes
    ax.set_xlim(x_min - 0.35 * dx, x_max + 0.04 * dx)
    ax.set_ylim(y_min - 0.03 * dy, y_max + 0.06 * dy)
    
    plt.tight_layout()
    Path(output_png).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_png, dpi=dpi, bbox_inches='tight', pad_inches=0.06)
    plt.savefig(output_pdf, bbox_inches='tight', pad_inches=0.06)
    plt.close()
    print(f"Generated clean Dhaka plot: {output_png} & {output_pdf}")


if __name__ == "__main__":
    selected_homes, zone_indices = load_and_sample_dhaka_homes()
    
    # Save the exact 1,000 homes metadata for artifact evaluation
    with open("data/dhaka_sampled_1000_homes.json", "w", encoding="utf-8") as f:
        json.dump(selected_homes, f, indent=2)
    print("Saved exact sample to data/dhaka_sampled_1000_homes.json")
    
    G, pos, is_bridge, e_s2s, e_b2b, e_s2b, homes = build_dhaka_iot_mesh_topology(selected_homes, zone_indices)
    
    # Render final publication graphics
    render_dhaka_publication_plot(
        G, pos, is_bridge, e_s2s, e_b2b, e_s2b,
        output_png="plots/fig_1000_nodes_topology_v2_clean.png",
        output_pdf="plots/fig_1000_nodes_topology_v2_clean.pdf"
    )
    
    # Also save with title for supplementary documentation
    render_dhaka_publication_plot(
        G, pos, is_bridge, e_s2s, e_b2b, e_s2b,
        output_png="plots/fig_1000_nodes_topology_v2_iot.png",
        output_pdf="plots/fig_1000_nodes_topology_v2_iot.pdf"
    )
