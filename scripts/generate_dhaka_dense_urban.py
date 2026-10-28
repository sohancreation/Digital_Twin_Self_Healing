import json
import numpy as np
import networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from pathlib import Path
from scipy.spatial import KDTree
from sklearn.cluster import KMeans

matplotlib.rcParams['font.family'] = 'serif'
matplotlib.rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif', 'Times']
matplotlib.rcParams['mathtext.fontset'] = 'cm'
matplotlib.rcParams['pdf.fonttype'] = 42
matplotlib.rcParams['ps.fonttype'] = 42

def generate_dhaka_dense_urban_refined(seed=142):
    with open("data/dhaka_real_1000_buildings.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        
    # Contiguous South-West Dhaka: Dhanmondi, Lalmatia, Mohammadpur
    subset = [d for d in data if d['zone'] in ('Dhanmondi', 'Lalmatia_Mohammadpur')]
    
    rng = np.random.default_rng(seed)
    
    # Stratified sampling of 1000 real buildings
    chosen_indices = rng.choice(len(subset), 1000, replace=False)
    selected_homes = [subset[i] for i in chosen_indices]
    
    # Save the exact sampled 1000 buildings metadata
    with open("data/dhaka_1000_homes_sampled.json", "w", encoding="utf-8") as f:
        json.dump(selected_homes, f, indent=2)
        
    coords = np.array([[h['lon'], h['lat']] for h in selected_homes])
    
    # Real physical coordinate scaling to km (Dhaka coordinates)
    x_km = (coords[:, 0] - coords[:, 0].min()) * 101.9
    y_km = (coords[:, 1] - coords[:, 1].min()) * 110.8
    
    scale = max(x_km.max(), y_km.max())
    positions = {i: np.array([x_km[i] / scale, y_km[i] / scale]) for i in range(1000)}
    pos_arr = np.array([positions[i] for i in range(1000)])
    
    # Spatial clustering into 9 cohesive urban neighborhoods (Dhanmondi R/A sectors, Lalmatia blocks, etc.)
    kmeans = KMeans(n_clusters=9, random_state=seed, n_init=10).fit(pos_arr)
    labels = kmeans.labels_
    
    is_bridge = np.zeros(1000, dtype=bool)
    cluster_gateways = {}
    
    for c in range(9):
        c_nodes = np.where(labels == c)[0]
        c_pos = pos_arr[c_nodes]
        c_center = kmeans.cluster_centers_[c]
        dists = np.linalg.norm(c_pos - c_center, axis=1)
        sorted_idx = np.argsort(dists)
        
        # 16% gateway hubs in each neighborhood cluster
        n_gw = max(10, int(len(c_nodes) * 0.16))
        gw_nodes = [c_nodes[i] for i in sorted_idx[:n_gw]]
        for gw in gw_nodes:
            is_bridge[gw] = True
        cluster_gateways[c] = gw_nodes
        
    G = nx.Graph()
    G.add_nodes_from(range(1000))
    kdtree = KDTree(pos_arr)
    
    # 1. Sensor-to-Sensor (Green links): Dense mesh within each neighborhood
    for c in range(9):
        c_nodes = np.where(labels == c)[0]
        c_sensors = [n for n in c_nodes if not is_bridge[n]]
        if len(c_sensors) > 1:
            c_pos = pos_arr[c_sensors]
            for idx, u in enumerate(c_sensors):
                dists = np.linalg.norm(c_pos - c_pos[idx], axis=1)
                k_mesh = rng.integers(3, 7)
                near_idx = np.argsort(dists)[1:k_mesh + 1]
                for ni in near_idx:
                    if dists[ni] < 0.15:
                        G.add_edge(u, c_sensors[ni])
                        
    # Connect adjacent clusters for sensors
    adj_clusters = [
        (0, 1), (0, 2), (1, 2), (1, 3), (2, 3),
        (2, 4), (3, 5), (4, 5), (4, 6), (5, 6),
        (5, 7), (6, 7), (7, 8), (0, 4), (1, 8)
    ]
    for c1, c2 in adj_clusters:
        s1_list = [n for n in np.where(labels == c1)[0] if not is_bridge[n]]
        s2_list = [n for n in np.where(labels == c2)[0] if not is_bridge[n]]
        if s1_list and s2_list:
            for _ in range(rng.integers(6, 12)):
                u = rng.choice(s1_list)
                dists = [np.linalg.norm(pos_arr[u] - pos_arr[v]) for v in s2_list]
                min_v = s2_list[np.argmin(dists)]
                if min(dists) < 0.18:
                    G.add_edge(u, min_v)
                    
    # 2. Sensor-to-Bridge Uplinks (Brown links):
    # Each gateway connects to 3-6 nearest sensor nodes in its cluster
    for c in range(9):
        gws = cluster_gateways[c]
        c_sensors = [n for n in np.where(labels == c)[0] if not is_bridge[n]]
        if c_sensors:
            s_pos = pos_arr[c_sensors]
            for gw in gws:
                dists = np.linalg.norm(s_pos - pos_arr[gw], axis=1)
                k_att = min(len(c_sensors), rng.integers(3, 6))
                nearest_s = np.argsort(dists)[:k_att]
                for si in nearest_s:
                    if dists[si] < 0.16:
                        G.add_edge(gw, c_sensors[si])
                        
    # 3. Gateway-to-Gateway Backbone (Orange links):
    # Intra-cluster gateway mesh
    for c in range(9):
        gws = cluster_gateways[c]
        if len(gws) > 1:
            for gw1 in gws:
                dists = [np.linalg.norm(pos_arr[gw1] - pos_arr[gw2]) for gw2 in gws]
                near_gw = np.argsort(dists)[1:min(4, len(gws))]
                for ngw in near_gw:
                    G.add_edge(gw1, gws[ngw])
                    
    # Inter-cluster gateway backbone routes
    for c1, c2 in adj_clusters:
        gw1_list = cluster_gateways[c1]
        gw2_list = cluster_gateways[c2]
        n_links = rng.integers(1, 4)
        for _ in range(n_links):
            gw1 = rng.choice(gw1_list)
            dists = [np.linalg.norm(pos_arr[gw1] - pos_arr[gw2]) for gw2 in gw2_list]
            gw2 = gw2_list[np.argmin(dists)]
            G.add_edge(gw1, gw2)
            
    # Guarantee global connectivity
    if not nx.is_connected(G):
        comps = list(nx.connected_components(G))
        for k in range(len(comps) - 1):
            comp_a = list(comps[k])
            comp_b = list(comps[k + 1])
            min_d = float('inf')
            best = (comp_a[0], comp_b[0])
            for u in comp_a[:25]:
                for v in comp_b[:25]:
                    d = np.linalg.norm(pos_arr[u] - pos_arr[v])
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
    print(f"Refined Dhaka Urban Graph: |V| = {G.number_of_nodes()}, |E| = {G.number_of_edges()}")
    print(f"  Sensors: {sensor_count}, Gateways: {bridge_count}")
    print(f"  Green (S2S): {len(e_s2s)}, Orange (B2B): {len(e_b2b)}, Brown (S2B): {len(e_s2b)}")
    
    # Publication plot with exact aspect ratio 1.302
    fig, ax = plt.subplots(figsize=(7.5, 5.76), dpi=300)
    ax.set_facecolor('white')
    fig.patch.set_facecolor('white')
    
    c_green = '#2e7d32'   # Forest Green
    c_orange = '#f39c12'  # Amber Orange
    c_brown = '#8b2500'   # Sienna Brown
    c_blue = '#0026e6'    # Blue (Sensors)
    c_red = '#e60000'     # Red (Gateways)
    
    for u, v in e_s2s:
        ax.plot([pos_arr[u, 0], pos_arr[v, 0]], [pos_arr[u, 1], pos_arr[v, 1]],
                color=c_green, linewidth=0.55, alpha=0.68, zorder=1)
                
    for u, v in e_b2b:
        ax.plot([pos_arr[u, 0], pos_arr[v, 0]], [pos_arr[u, 1], pos_arr[v, 1]],
                color=c_orange, linewidth=0.90, alpha=0.84, zorder=2)
                
    for u, v in e_s2b:
        ax.plot([pos_arr[u, 0], pos_arr[v, 0]], [pos_arr[u, 1], pos_arr[v, 1]],
                color=c_brown, linewidth=0.75, alpha=0.78, zorder=2)
                
    s_idx = np.where(~is_bridge)[0]
    b_idx = np.where(is_bridge)[0]
    
    ax.scatter(pos_arr[s_idx, 0], pos_arr[s_idx, 1], c=c_blue, s=6.5, zorder=3, edgecolors='none')
    ax.scatter(pos_arr[b_idx, 0], pos_arr[b_idx, 1], c=c_red, s=11.5, zorder=4, edgecolors='none')
    
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', label="IoT Sensor Node",
               markerfacecolor=c_blue, markersize=10.0),
        Line2D([0], [0], marker='o', color='w', label="Bridge / Gateway",
               markerfacecolor=c_red, markersize=10.0),
        Line2D([0], [1], color=c_green, lw=2.5, label="Sensor-to-Sensor Link"),
        Line2D([0], [1], color=c_orange, lw=2.5, label="Bridge-to-Bridge Link"),
        Line2D([0], [1], color=c_brown, lw=2.5, label="Sensor-to-Bridge Link"),
    ]
    
    leg = ax.legend(
        handles=legend_elements,
        loc='lower left',
        bbox_to_anchor=(0.01, 0.03),
        frameon=True,
        framealpha=0.96,
        edgecolor='#64748b',
        fontsize=12.5,
        labelspacing=0.45,
        handlelength=1.6,
        handletextpad=0.6,
        borderpad=0.6
    )
    leg.get_frame().set_linewidth(1.3)
    ax.axis('off')
    
    x_min, x_max = pos_arr[:, 0].min(), pos_arr[:, 0].max()
    y_min, y_max = pos_arr[:, 1].min(), pos_arr[:, 1].max()
    dx = x_max - x_min
    dy = y_max - y_min
    ax.set_xlim(x_min - 0.38 * dx, x_max + 0.03 * dx)
    ax.set_ylim(y_min - 0.03 * dy, y_max + 0.03 * dy)
    
    plt.tight_layout()
    
    # Save as the official Fig 7 files:
    out_clean_png = "plots/fig_1000_nodes_topology_v2_clean.png"
    out_clean_pdf = "plots/fig_1000_nodes_topology_v2_clean.pdf"
    plt.savefig(out_clean_png, dpi=300, bbox_inches='tight', pad_inches=0.06)
    plt.savefig(out_clean_pdf, bbox_inches='tight', pad_inches=0.06)
    plt.close()
    print(f"Generated official Fig 7: {out_clean_png} and {out_clean_pdf}")
    
    return G

if __name__ == "__main__":
    generate_dhaka_dense_urban_refined()
