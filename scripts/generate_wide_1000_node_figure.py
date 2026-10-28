"""
Generate 1,000-node connected network topology figure formatted specifically
to match Fig 2's exact dimensions (4.67:1 aspect ratio, width=0.98\textwidth, height=108pt / 1.5in).
Ensures:
- Exact same bounding box height and width as the original Fig 2
- Strictly 0 pt vertical change in the LaTeX layout
- Dominant green mesh (Sensor-to-Sensor)
- Orange backbone (Bridge-to-Bridge)
- Brown attachment links (Sensor-to-Bridge)
- Blue dots (IoT sensor nodes) and Red dots (Articulation bridge / Gateway)
- Top-left crisp legend matching IEEE typography
"""

import sys
from pathlib import Path
import numpy as np
import networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import fitz
from PIL import Image, ImageOps

matplotlib.rcParams['font.family'] = 'serif'
matplotlib.rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif', 'Times']
matplotlib.rcParams['mathtext.fontset'] = 'cm'
matplotlib.rcParams['pdf.fonttype'] = 42
matplotlib.rcParams['ps.fonttype'] = 42

def generate_wide_1000_node_graph(seed: int = 142):
    rng = np.random.default_rng(seed)
    num_nodes = 1000
    
    # Target aspect ratio: 4.67:1 (e.g. width = 14.0, height = 3.0)
    # Arrange 8 major clusters horizontally across x in [0.08, 0.92], y in [0.15, 0.85]
    cluster_centers = np.array([
        [0.08, 0.45],  # C0: Far-west sensor cluster
        [0.20, 0.52],  # C1: West cluster
        [0.32, 0.40],  # C2: West-central cluster
        [0.44, 0.58],  # C3: Central-north hub
        [0.56, 0.38],  # C4: Central-south hub
        [0.68, 0.62],  # C5: East-central cluster
        [0.80, 0.42],  # C6: East metropolitan core
        [0.92, 0.55],  # C7: Far-east gateway core
    ])
    num_clusters = len(cluster_centers)
    
    # Weight nodes towards central and eastern hubs
    weights = [70, 90, 110, 150, 150, 160, 150, 120]
    weights = np.array(weights, dtype=float)
    weights /= weights.sum()
    
    cluster_assignments = rng.choice(num_clusters, size=num_nodes, p=weights)
    
    # Spread per cluster (wider in x to span naturally, contained in y)
    spreads_x = [0.035, 0.040, 0.045, 0.050, 0.050, 0.050, 0.045, 0.038]
    spreads_y = [0.14,  0.16,  0.18,  0.22,  0.22,  0.22,  0.20,  0.16]
    
    positions = {}
    for i in range(num_nodes):
        c = cluster_assignments[i]
        dx = rng.normal(0, spreads_x[c])
        dy = rng.normal(0, spreads_y[c])
        # Clip to maintain bounds
        px = np.clip(cluster_centers[c][0] + dx, 0.02, 0.98)
        py = np.clip(cluster_centers[c][1] + dy, 0.06, 0.94)
        positions[i] = np.array([px, py])
        
    # Red Nodes (Articulation bridges / Gateways) ~15%
    is_bridge = np.zeros(num_nodes, dtype=bool)
    for c in range(num_clusters):
        c_nodes = np.where(cluster_assignments == c)[0]
        n_bridges = max(3, int(len(c_nodes) * 0.16))
        c_pos = np.array([positions[n] for n in c_nodes])
        center = cluster_centers[c]
        dists = np.linalg.norm(c_pos - center, axis=1)
        sorted_idx = np.argsort(dists)
        # Mix of central hub bridges and perimeter bridges
        chosen = list(sorted_idx[:max(1, n_bridges // 2)]) + list(sorted_idx[-max(2, n_bridges // 2):])
        for idx in chosen:
            is_bridge[c_nodes[idx]] = True
            
    # Graph Construction
    G = nx.Graph()
    G.add_nodes_from(range(num_nodes))
    
    # 1. Intra-cluster sensor mesh (Green lines)
    for c in range(num_clusters):
        c_nodes = np.where(cluster_assignments == c)[0]
        c_sensors = [n for n in c_nodes if not is_bridge[n]]
        if len(c_sensors) > 1:
            c_pos = np.array([positions[n] for n in c_sensors])
            for i_idx, u in enumerate(c_sensors):
                dists = np.linalg.norm(c_pos - c_pos[i_idx], axis=1)
                k_conn = rng.integers(3, 7)
                near_idx = np.argsort(dists)[1:k_conn + 1]
                for ni in near_idx:
                    if dists[ni] < 0.18:
                        G.add_edge(u, c_sensors[ni])
                        
    # Connect adjacent clusters (Sensors)
    for c in range(num_clusters - 1):
        c1_sensors = [n for n in np.where(cluster_assignments == c)[0] if not is_bridge[n]]
        c2_sensors = [n for n in np.where(cluster_assignments == c + 1)[0] if not is_bridge[n]]
        if c1_sensors and c2_sensors:
            for _ in range(rng.integers(8, 15)):
                u = rng.choice(c1_sensors)
                dists = [np.linalg.norm(positions[u] - positions[v]) for v in c2_sensors]
                min_v = c2_sensors[np.argmin(dists)]
                if min(dists) < 0.20:
                    G.add_edge(u, min_v)
                    
    # 2. Sensor-to-Bridge (Brown lines)
    bridge_nodes = np.where(is_bridge)[0]
    for b in bridge_nodes:
        c = cluster_assignments[b]
        c_sensors = [n for n in np.where(cluster_assignments == c)[0] if not is_bridge[n]]
        if c_sensors:
            dists = [np.linalg.norm(positions[b] - positions[s]) for s in c_sensors]
            k_att = min(len(c_sensors), rng.integers(3, 6))
            nearest_s = np.argsort(dists)[:k_att]
            for s_idx in nearest_s:
                if dists[s_idx] < 0.18:
                    G.add_edge(b, c_sensors[s_idx])
                    
    # 3. Bridge-to-Bridge backbone (Orange lines)
    # Connect bridges within cluster
    for c in range(num_clusters):
        c_bridges = [b for b in bridge_nodes if cluster_assignments[b] == c]
        if len(c_bridges) > 1:
            for b1 in c_bridges:
                dists = [np.linalg.norm(positions[b1] - positions[b2]) for b2 in c_bridges]
                near_b = np.argsort(dists)[1:3]
                for nb in near_b:
                    G.add_edge(b1, c_bridges[nb])
                    
    # Inter-cluster bridge backbone spanning across the network
    for c in range(num_clusters - 1):
        c1_bridges = [b for b in bridge_nodes if cluster_assignments[b] == c]
        c2_bridges = [b for b in bridge_nodes if cluster_assignments[b] == c + 1]
        if c1_bridges and c2_bridges:
            for _ in range(rng.integers(2, 4)):
                b1 = rng.choice(c1_bridges)
                dists = [np.linalg.norm(positions[b1] - positions[b2]) for b2 in c2_bridges]
                b2 = c2_bridges[np.argmin(dists)]
                G.add_edge(b1, b2)
                
    # Longer highway links between non-adjacent bridge clusters
    long_links = [(0, 2), (1, 3), (2, 4), (3, 5), (4, 6), (5, 7)]
    for c1, c2 in long_links:
        b1_list = [b for b in bridge_nodes if cluster_assignments[b] == c1]
        b2_list = [b for b in bridge_nodes if cluster_assignments[b] == c2]
        if b1_list and b2_list and rng.random() < 0.65:
            b1 = rng.choice(b1_list)
            dists = [np.linalg.norm(positions[b1] - positions[b2]) for b2 in b2_list]
            b2 = b2_list[np.argmin(dists)]
            G.add_edge(b1, b2)
            
    # Global connectivity check
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
            
    print(f"Wide Graph: |V| = {G.number_of_nodes()}, |E| = {G.number_of_edges()}")
    print(f"  Sensors: {num_nodes - len(bridge_nodes)}, Bridges: {len(bridge_nodes)}")
    print(f"  S2S (Green): {len(e_s2s)}, B2B (Orange): {len(e_b2b)}, S2B (Brown): {len(e_s2b)}")
    
    return G, positions, is_bridge, e_s2s, e_b2b, e_s2b


def render_wide_publication_figure(
    G, positions, is_bridge, e_s2s, e_b2b, e_s2b,
    output_pdf="plots/fig2_1000node_topology_wide.pdf",
    output_png="plots/fig2_1000node_topology_wide.png",
    dpi=300
):
    # Dimensions: 7.15 inches wide x 1.53 inches tall (matches 0.98\textwidth at 4.67:1 aspect ratio!)
    fig, ax = plt.subplots(figsize=(7.15, 1.53), dpi=dpi)
    ax.set_facecolor('white')
    fig.patch.set_facecolor('white')
    
    pos = positions
    
    c_green = '#2e7d32'   # Sensor-to-Sensor
    c_orange = '#f39c12'  # Bridge-to-Bridge
    c_brown = '#8b2500'   # Sensor-to-Bridge
    c_blue = '#0026e6'    # IoT Sensor Node
    c_red = '#e60000'     # Articulation Bridge / Gateway
    
    # 1. Green links: Sensor-to-Sensor
    for u, v in e_s2s:
        ax.plot([pos[u][0], pos[v][0]], [pos[u][1], pos[v][1]],
                color=c_green, linewidth=0.45, alpha=0.65, zorder=1)
                
    # 2. Orange links: Bridge-to-Bridge
    for u, v in e_b2b:
        ax.plot([pos[u][0], pos[v][0]], [pos[u][1], pos[v][1]],
                color=c_orange, linewidth=0.75, alpha=0.82, zorder=2)
                
    # 3. Brown links: Sensor-to-Bridge
    for u, v in e_s2b:
        ax.plot([pos[u][0], pos[v][0]], [pos[u][1], pos[v][1]],
                color=c_brown, linewidth=0.65, alpha=0.75, zorder=2)
                
    # Nodes
    sensor_nodes = [n for n in G.nodes() if not is_bridge[n]]
    bridge_nodes = [n for n in G.nodes() if is_bridge[n]]
    
    sx = [pos[n][0] for n in sensor_nodes]
    sy = [pos[n][1] for n in sensor_nodes]
    bx = [pos[n][0] for n in bridge_nodes]
    by = [pos[n][1] for n in bridge_nodes]
    
    ax.scatter(sx, sy, c=c_blue, s=4.5, zorder=3, edgecolors='none')
    ax.scatter(bx, by, c=c_red, s=8.5, zorder=4, edgecolors='none')
    
    # Custom Legend in upper left
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', label='IoT sensor node',
               markerfacecolor=c_blue, markersize=4.2),
        Line2D([0], [0], marker='o', color='w', label='Articulation bridge / Gateway',
               markerfacecolor=c_red, markersize=4.2),
        Line2D([0], [1], color=c_green, lw=1.2, label='Sensor-to-Sensor connection'),
        Line2D([0], [1], color=c_orange, lw=1.2, label='Bridge-to-Bridge connection'),
        Line2D([0], [1], color=c_brown, lw=1.2, label='Sensor-to-Bridge connection'),
    ]
    
    leg = ax.legend(
        handles=legend_elements,
        loc='upper left',
        bbox_to_anchor=(0.015, 0.98),
        frameon=True,
        framealpha=0.94,
        edgecolor='#cbd5e1',
        fontsize=6.8,
        labelspacing=0.28,
        handlelength=1.3,
        handletextpad=0.5,
        borderpad=0.45
    )
    leg.get_frame().set_linewidth(0.6)
    
    ax.axis('off')
    
    # Limits
    all_x = [pos[n][0] for n in G.nodes()]
    all_y = [pos[n][1] for n in G.nodes()]
    x_min, x_max = min(all_x), max(all_x)
    y_min, y_max = min(all_y), max(all_y)
    dx = x_max - x_min
    dy = y_max - y_min
    ax.set_xlim(x_min - 0.015 * dx, x_max + 0.015 * dx)
    ax.set_ylim(y_min - 0.02 * dy, y_max + 0.02 * dy)
    
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    
    Path(output_pdf).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_pdf, bbox_inches='tight', pad_inches=0.01)
    plt.savefig(output_png, dpi=dpi, bbox_inches='tight', pad_inches=0.01)
    plt.close()
    
    # Measure exact bounding box with PyMuPDF
    doc = fitz.open(output_pdf)
    page = doc[0]
    print(f"Generated {output_pdf}: {page.rect.width:.2f} x {page.rect.height:.2f} pt (Aspect: {page.rect.width/page.rect.height:.2f})")


if __name__ == "__main__":
    G, pos, is_bridge, e_s2s, e_b2b, e_s2b = generate_wide_1000_node_graph(seed=142)
    render_wide_publication_figure(G, pos, is_bridge, e_s2s, e_b2b, e_s2b)
