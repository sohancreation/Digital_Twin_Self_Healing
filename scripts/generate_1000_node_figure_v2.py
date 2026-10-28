"""
High-Fidelity 1,000-Node Connected Network Topology Generator.
Precisely matches the topological characteristics, edge color distribution,
and visual aesthetics of the reference figure:
- Dominant green mesh (Sensor-to-Sensor / Power-to-Power)
- Clean, long-range orange backbone (Bridge-to-Bridge / EVCS-to-EVCS)
- Concentrated brown attachment links (Sensor-to-Bridge / Power-to-EVCS)
- Distinct dense core clusters + perimeter branches + westward tail
"""

import sys
from pathlib import Path
import numpy as np
import networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

# Publication typography
matplotlib.rcParams['font.family'] = 'serif'
matplotlib.rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif', 'Times']
matplotlib.rcParams['mathtext.fontset'] = 'cm'
matplotlib.rcParams['pdf.fonttype'] = 42
matplotlib.rcParams['ps.fonttype'] = 42

def generate_1000_node_graph_v2(seed: int = 142):
    rng = np.random.default_rng(seed)
    num_nodes = 1000
    
    # Define cluster centers matching the reference layout
    # Reference shape:
    # - C0: Major dense core 1 (east-central)
    # - C1: Major dense core 2 (southeast)
    # - C2: Major dense core 3 (south-central)
    # - C3: Major dense core 4 (northeast)
    # - C4: North perimeter / ridge
    # - C5: Northwest shoulder
    # - C6: Central transit corridor
    # - C7: Southwest branch
    # - C8: Far-west elongated tail
    cluster_centers = np.array([
        [0.72, 0.62],  # C0: Core Northeast
        [0.82, 0.38],  # C1: Core East
        [0.60, 0.38],  # C2: Core South-Central
        [0.68, 0.18],  # C3: Core South
        [0.46, 0.82],  # C4: North Ridge
        [0.38, 0.64],  # C5: Northwest Shoulder
        [0.50, 0.50],  # C6: Central Transit Corridor
        [0.24, 0.44],  # C7: Southwest Branch
        [0.08, 0.42],  # C8: Far-West Tail
    ])
    num_clusters = len(cluster_centers)
    
    # Node population distribution across clusters
    # Cores C0-C3 contain the majority of nodes (~70%)
    weights = [220, 200, 180, 120, 70, 70, 60, 50, 30]
    weights = np.array(weights, dtype=float)
    weights /= weights.sum()
    
    cluster_assignments = rng.choice(num_clusters, size=num_nodes, p=weights)
    
    spreads = [0.055, 0.050, 0.050, 0.045, 0.065, 0.055, 0.060, 0.050, 0.028]
    positions = {}
    
    for i in range(num_nodes):
        c = cluster_assignments[i]
        sigma = spreads[c]
        if c == 8:  # Tail is elongated horizontally
            dx = rng.uniform(-0.06, 0.06)
            dy = rng.normal(0, sigma * 0.35)
        else:
            dx = rng.normal(0, sigma)
            dy = rng.normal(0, sigma)
        positions[i] = cluster_centers[c] + np.array([dx, dy])
        
    # Classify Red Nodes (Bridges / EVCS):
    # In the reference image, red nodes form dense clusters inside the core clusters (EVCS hubs)
    # plus key perimeter articulation points
    is_bridge = np.zeros(num_nodes, dtype=bool)
    
    # 1. Core EVCS / Gateway hubs in C0, C1, C2, C3
    for c in [0, 1, 2, 3]:
        c_nodes = np.where(cluster_assignments == c)[0]
        # Pick 20-30 tightly clustered bridge nodes at core center
        c_pos = np.array([positions[n] for n in c_nodes])
        center = cluster_centers[c]
        dists = np.linalg.norm(c_pos - center, axis=1)
        sorted_idx = np.argsort(dists)
        # Select dense core of red nodes (like the dense red clusters in the example!)
        n_hub_bridges = int(len(c_nodes) * 0.20)
        for idx in sorted_idx[:n_hub_bridges]:
            is_bridge[c_nodes[idx]] = True
            
    # 2. Perimeter bridges in C4, C5, C6, C7, C8
    for c in [4, 5, 6, 7, 8]:
        c_nodes = np.where(cluster_assignments == c)[0]
        n_p_bridges = max(2, int(len(c_nodes) * 0.12))
        chosen = rng.choice(c_nodes, n_p_bridges, replace=False)
        for n in chosen:
            is_bridge[n] = True
            
    bridge_count = np.sum(is_bridge)
    sensor_count = num_nodes - bridge_count
    
    # Construct Graph Edges
    G = nx.Graph()
    G.add_nodes_from(range(num_nodes))
    
    # (A) Sensor-to-Sensor (Green lines) - Dense wireless mesh within clusters
    # Each sensor connects to its 3 to 6 nearest sensor neighbors
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
                    if dists[ni] < 0.14:
                        G.add_edge(u, c_sensors[ni])
                        
    # Connect adjacent clusters for sensors
    cluster_pairs = [
        (0, 1), (0, 2), (0, 6),
        (1, 2), (1, 3), (2, 3), (2, 6),
        (4, 5), (4, 6), (5, 6), (5, 7), (7, 8)
    ]
    for c1, c2 in cluster_pairs:
        c1_sensors = [n for n in np.where(cluster_assignments == c1)[0] if not is_bridge[n]]
        c2_sensors = [n for n in np.where(cluster_assignments == c2)[0] if not is_bridge[n]]
        if c1_sensors and c2_sensors:
            for _ in range(rng.integers(6, 12)):
                u = rng.choice(c1_sensors)
                dists = [np.linalg.norm(positions[u] - positions[v]) for v in c2_sensors]
                min_v = c2_sensors[np.argmin(dists)]
                if min(dists) < 0.22:
                    G.add_edge(u, min_v)
                    
    # (B) Sensor-to-Bridge / Power-to-EVCS (Brown lines)
    # Each bridge connects to 3-6 nearest sensor nodes in its cluster
    bridge_nodes = np.where(is_bridge)[0]
    for b in bridge_nodes:
        c = cluster_assignments[b]
        c_sensors = [n for n in np.where(cluster_assignments == c)[0] if not is_bridge[n]]
        if c_sensors:
            dists = [np.linalg.norm(positions[b] - positions[s]) for s in c_sensors]
            k_att = min(len(c_sensors), rng.integers(3, 6))
            nearest_s = np.argsort(dists)[:k_att]
            for s_idx in nearest_s:
                if dists[s_idx] < 0.16:
                    G.add_edge(b, c_sensors[s_idx])
                    
    # (C) Bridge-to-Bridge / EVCS-to-EVCS (Orange lines)
    # 1. Intra-core bridge mesh (connect bridges within each core hub)
    for c in [0, 1, 2, 3]:
        c_bridges = [b for b in bridge_nodes if cluster_assignments[b] == c]
        if len(c_bridges) > 1:
            for b1 in c_bridges:
                dists = [np.linalg.norm(positions[b1] - positions[b2]) for b2 in c_bridges]
                near_b = np.argsort(dists)[1:4]
                for nb in near_b:
                    G.add_edge(b1, c_bridges[nb])
                    
    # 2. Inter-cluster long-range bridge backbone (Orange lines spanning clusters and perimeter)
    # As visible in the reference figure, orange lines connect across the northern perimeter,
    # from west to core, and between the core hubs.
    bridge_routes = [
        (8, 7), (7, 5), (5, 4), (4, 0),  # North / West perimeter highway
        (7, 6), (5, 6), (6, 0), (6, 2),  # Central highway
        (0, 1), (1, 3), (2, 3), (0, 2),  # Core inter-hub highway
        (8, 6), (7, 2), (4, 1)           # Long-distance cross-links
    ]
    
    for c1, c2 in bridge_routes:
        b1_list = [b for b in bridge_nodes if cluster_assignments[b] == c1]
        b2_list = [b for b in bridge_nodes if cluster_assignments[b] == c2]
        if b1_list and b2_list:
            n_links = rng.integers(1, 4)
            for _ in range(n_links):
                b1 = rng.choice(b1_list)
                dists = [np.linalg.norm(positions[b1] - positions[b2]) for b2 in b2_list]
                b2 = b2_list[np.argmin(dists)]
                G.add_edge(b1, b2)
                
    # Ensure global connectivity
    if not nx.is_connected(G):
        comps = list(nx.connected_components(G))
        for k in range(len(comps) - 1):
            comp_a = list(comps[k])
            comp_b = list(comps[k + 1])
            min_d = float('inf')
            best = (comp_a[0], comp_b[0])
            for u in comp_a[:30]:
                for v in comp_b[:30]:
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
            
    print(f"[v2] Graph: |V| = {G.number_of_nodes()}, |E| = {G.number_of_edges()}")
    print(f"  Sensor Nodes: {sensor_count}, Bridge Nodes: {bridge_count}")
    print(f"  Green (S2S): {len(e_s2s)}, Orange (B2B): {len(e_b2b)}, Brown (S2B): {len(e_s2b)}")
    
    return G, positions, is_bridge, e_s2s, e_b2b, e_s2b


def render_publication_plot(
    G, positions, is_bridge, e_s2s, e_b2b, e_s2b,
    output_png="plots/fig_1000_nodes_topology_v2.png",
    output_pdf="plots/fig_1000_nodes_topology_v2.pdf",
    node_labels=("IoT sensor node", "Articulation bridge / Gateway"),
    edge_labels=("Sensor-to-Sensor connection", "Bridge-to-Bridge connection", "Sensor-to-Bridge connection"),
    fig_title="Fig. 2.  Undirected connected graph structure for power and EVCS nodes",
    dpi=300
):
    fig, ax = plt.subplots(figsize=(7.5, 5.8), dpi=dpi)
    ax.set_facecolor('white')
    fig.patch.set_facecolor('white')
    
    pos = positions
    
    # Edge colors exactly matching reference:
    # Green: #2e7d32 (Forest Green)
    # Orange: #f59e0b / #e67e22 (Vibrant Amber / Orange)
    # Brown: #8b2500 / #a04000 (Rich Sienna Brown)
    c_green = '#2e7d32'
    c_orange = '#f39c12'
    c_brown = '#8b2500'
    
    # 1. Green links: Sensor-to-Sensor
    for u, v in e_s2s:
        ax.plot([pos[u][0], pos[v][0]], [pos[u][1], pos[v][1]],
                color=c_green, linewidth=0.55, alpha=0.68, zorder=1)
                
    # 2. Orange links: Bridge-to-Bridge
    for u, v in e_b2b:
        ax.plot([pos[u][0], pos[v][0]], [pos[u][1], pos[v][1]],
                color=c_orange, linewidth=0.85, alpha=0.82, zorder=2)
                
    # 3. Brown links: Sensor-to-Bridge
    for u, v in e_s2b:
        ax.plot([pos[u][0], pos[v][0]], [pos[u][1], pos[v][1]],
                color=c_brown, linewidth=0.75, alpha=0.78, zorder=2)
                
    # Nodes:
    # Blue: #0026e6, Red: #e60000
    c_blue = '#0026e6'
    c_red = '#e60000'
    
    sensor_nodes = [n for n in G.nodes() if not is_bridge[n]]
    bridge_nodes = [n for n in G.nodes() if is_bridge[n]]
    
    sx = [pos[n][0] for n in sensor_nodes]
    sy = [pos[n][1] for n in sensor_nodes]
    bx = [pos[n][0] for n in bridge_nodes]
    by = [pos[n][1] for n in bridge_nodes]
    
    ax.scatter(sx, sy, c=c_blue, s=6.5, zorder=3, edgecolors='none')
    ax.scatter(bx, by, c=c_red, s=11.5, zorder=4, edgecolors='none')
    
    # Custom Legend - enhanced for column-width legibility without blocking any nodes or edges
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', label=node_labels[0],
               markerfacecolor=c_blue, markersize=10.0),
        Line2D([0], [0], marker='o', color='w', label=node_labels[1],
               markerfacecolor=c_red, markersize=10.0),
        Line2D([0], [1], color=c_green, lw=2.5, label=edge_labels[0]),
        Line2D([0], [1], color=c_orange, lw=2.5, label=edge_labels[1]),
        Line2D([0], [1], color=c_brown, lw=2.5, label=edge_labels[2]),
    ]
    
    leg = ax.legend(
        handles=legend_elements,
        loc='upper left',
        bbox_to_anchor=(0.01, 0.99),
        frameon=True,
        framealpha=0.96,
        edgecolor='#64748b',
        fontsize=13.5,
        labelspacing=0.45,
        handlelength=1.6,
        handletextpad=0.6,
        borderpad=0.6
    )
    leg.get_frame().set_linewidth(1.3)
    
    ax.axis('off')
    
    all_x = [pos[n][0] for n in G.nodes()]
    all_y = [pos[n][1] for n in G.nodes()]
    x_min, x_max = min(all_x), max(all_x)
    y_min, y_max = min(all_y), max(all_y)
    dx = x_max - x_min
    dy = y_max - y_min
    ax.set_xlim(x_min - 0.38 * dx, x_max + 0.03 * dx)
    ax.set_ylim(y_min - 0.03 * dy, y_max + 0.06 * dy)
    
    plt.tight_layout()
    
    if fig_title:
        fig.text(0.5, 0.02, fig_title, ha='center', va='bottom', fontsize=10.5, fontfamily='serif')
        plt.subplots_adjust(bottom=0.07)
        
    Path(output_png).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_png, dpi=dpi, bbox_inches='tight', pad_inches=0.06)
    plt.savefig(output_pdf, bbox_inches='tight', pad_inches=0.06)
    plt.close()
    print(f"Saved: {output_png} and {output_pdf}")


if __name__ == "__main__":
    G, pos, is_bridge, e_s2s, e_b2b, e_s2b = generate_1000_node_graph_v2(seed=142)
    
    # 1. IoT Network terminology (for this paper's domain)
    render_publication_plot(
        G, pos, is_bridge, e_s2s, e_b2b, e_s2b,
        output_png="plots/fig_1000_nodes_topology_v2_iot.png",
        output_pdf="plots/fig_1000_nodes_topology_v2_iot.pdf",
        node_labels=("IoT Sensor Node", "Bridge / Gateway"),
        edge_labels=("Sensor-to-Sensor Link", "Bridge-to-Bridge Link", "Sensor-to-Bridge Link"),
        fig_title="Fig. 2.  Undirected connected graph structure for 1,000-node IoT sensor and gateway network"
    )
    
    # 2. Exact reference terminology (Power bus / EVCS bus) as attached
    render_publication_plot(
        G, pos, is_bridge, e_s2s, e_b2b, e_s2b,
        output_png="plots/fig_1000_nodes_topology_v2_power.png",
        output_pdf="plots/fig_1000_nodes_topology_v2_power.pdf",
        node_labels=("Power bus", "EVCS bus"),
        edge_labels=("Power-to-Power connection", "EVCS-to-EVCS connection", "Power-to-EVCS connection"),
        fig_title="Fig. 2.  Undirected connected graph structure for power and EVCS nodes"
    )
    
    # 3. Clean without title embedded (for LaTeX inclusion)
    render_publication_plot(
        G, pos, is_bridge, e_s2s, e_b2b, e_s2b,
        output_png="plots/fig_1000_nodes_topology_v2_clean.png",
        output_pdf="plots/fig_1000_nodes_topology_v2_clean.pdf",
        node_labels=("IoT Sensor Node", "Bridge / Gateway"),
        edge_labels=("Sensor-to-Sensor Link", "Bridge-to-Bridge Link", "Sensor-to-Bridge Link"),
        fig_title=None
    )
