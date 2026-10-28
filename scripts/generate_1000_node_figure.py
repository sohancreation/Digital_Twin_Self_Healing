"""
Generate publication-quality 1000-node connected network topology graph.
Matches the visual aesthetics, legend structure, color coding, and topology of the example figure:
- Blue dots: IoT sensor nodes (or Power bus)
- Red dots: Articulation bridge / Gateway nodes (or EVCS bus)
- Green lines: Sensor-to-Sensor connection (Power-to-Power)
- Orange lines: Bridge-to-Bridge connection (EVCS-to-EVCS)
- Brown lines: Sensor-to-Bridge connection (Power-to-EVCS)
"""

import sys
from pathlib import Path
import numpy as np
import networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

# Set up publication typography
matplotlib.rcParams['font.family'] = 'serif'
matplotlib.rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif', 'Times']
matplotlib.rcParams['mathtext.fontset'] = 'cm'
matplotlib.rcParams['pdf.fonttype'] = 42
matplotlib.rcParams['ps.fonttype'] = 42

def generate_1000_node_graph(seed: int = 101):
    rng = np.random.default_rng(seed)
    num_nodes = 1000
    
    # 1. Create realistic spatial cluster centers (geographical layout like the example)
    # The example has ~5-7 main clusters plus outlying regional branches
    cluster_centers = np.array([
        [0.72, 0.65],  # Dense top-right cluster
        [0.82, 0.38],  # Dense mid-right cluster
        [0.62, 0.38],  # Dense center-right cluster
        [0.68, 0.18],  # Bottom-right cluster
        [0.45, 0.80],  # Top-mid cluster
        [0.38, 0.60],  # Mid-left cluster
        [0.22, 0.45],  # West branch
        [0.08, 0.42],  # Far-west narrow arm (like in the example image)
    ])
    num_clusters = len(cluster_centers)
    
    # Cluster weights (number of nodes per cluster)
    weights = [260, 220, 180, 110, 80, 70, 50, 30]
    weights = np.array(weights, dtype=float)
    weights /= weights.sum()
    
    # Assign each node to a cluster
    cluster_assignments = rng.choice(num_clusters, size=num_nodes, p=weights)
    
    # Generate node positions around cluster centers with varying spreads
    spreads = [0.065, 0.055, 0.060, 0.050, 0.070, 0.060, 0.050, 0.035]
    positions = {}
    
    for i in range(num_nodes):
        c = cluster_assignments[i]
        sigma = spreads[c]
        if c == 7:  # Far-west arm is elongated horizontally
            dx = rng.normal(0, sigma * 1.8)
            dy = rng.normal(0, sigma * 0.4)
        else:
            dx = rng.normal(0, sigma)
            dy = rng.normal(0, sigma)
        positions[i] = cluster_centers[c] + np.array([dx, dy])
    
    # 2. Select Gateway / Articulation Bridge nodes (~12% of nodes, red dots)
    # In each cluster, select nodes near boundaries and central hubs as bridges
    is_bridge = np.zeros(num_nodes, dtype=bool)
    for c in range(num_clusters):
        c_nodes = np.where(cluster_assignments == c)[0]
        n_bridges = max(3, int(len(c_nodes) * 0.13))
        # Pick some close to center, some close to periphery
        c_pos = np.array([positions[n] for n in c_nodes])
        center = cluster_centers[c]
        dists = np.linalg.norm(c_pos - center, axis=1)
        # Sort by distance and pick mix of hub and boundary nodes
        sorted_idx = np.argsort(dists)
        chosen = list(sorted_idx[:max(1, n_bridges // 3)]) + list(sorted_idx[-max(2, 2 * n_bridges // 3):])
        for idx in chosen:
            is_bridge[c_nodes[idx]] = True

    # 3. Construct Graph Edges
    G = nx.Graph()
    G.add_nodes_from(range(num_nodes))
    
    # (a) Intra-cluster links (k-nearest neighbors or distance threshold)
    for c in range(num_clusters):
        c_nodes = np.where(cluster_assignments == c)[0]
        c_pos = np.array([positions[n] for n in c_nodes])
        
        # Connect each node to nearest neighbors
        for idx_i, u in enumerate(c_nodes):
            dists = np.linalg.norm(c_pos - c_pos[idx_i], axis=1)
            # Find nearest 3 to 6 neighbors
            k_neighbors = rng.integers(3, 7)
            near_indices = np.argsort(dists)[1:k_neighbors + 1]
            for ni in near_indices:
                if dists[ni] < 0.12:  # max range
                    G.add_edge(u, c_nodes[ni])
                    
    # (b) Inter-cluster bridge backbone connections (Orange lines: Bridge-to-Bridge)
    bridge_nodes = np.where(is_bridge)[0]
    bridge_pos = np.array([positions[b] for b in bridge_nodes])
    
    # Connect bridges between adjacent clusters
    adj_clusters = [
        (0, 1), (0, 2), (0, 4),
        (1, 2), (1, 3),
        (2, 3), (2, 5),
        (4, 5), (5, 6), (6, 7)
    ]
    
    for c1, c2 in adj_clusters:
        c1_bridges = [b for b in bridge_nodes if cluster_assignments[b] == c1]
        c2_bridges = [b for b in bridge_nodes if cluster_assignments[b] == c2]
        if c1_bridges and c2_bridges:
            # Connect 2-4 pairs of closest bridges between these clusters
            for b1 in c1_bridges:
                for b2 in c2_bridges:
                    d = np.linalg.norm(positions[b1] - positions[b2])
                    if d < 0.32:
                        if rng.random() < 0.35:
                            G.add_edge(b1, b2)
                            
    # (c) Ensure global connectivity
    if not nx.is_connected(G):
        components = list(nx.connected_components(G))
        for k in range(len(components) - 1):
            comp_a = list(components[k])
            comp_b = list(components[k + 1])
            # Find closest pair
            min_d = float('inf')
            best_pair = (comp_a[0], comp_b[0])
            # Sample subset for speed
            sample_a = rng.choice(comp_a, min(len(comp_a), 40), replace=False)
            sample_b = rng.choice(comp_b, min(len(comp_b), 40), replace=False)
            for u in sample_a:
                for v in sample_b:
                    d = np.linalg.norm(positions[u] - positions[v])
                    if d < min_d:
                        min_d = d
                        best_pair = (u, v)
            G.add_edge(best_pair[0], best_pair[1])
            
    # Classify edges into 3 categories:
    # 1. Sensor-to-Sensor (both non-bridge) -> Green
    # 2. Bridge-to-Bridge (both bridge) -> Orange
    # 3. Sensor-to-Bridge (one bridge, one non-bridge) -> Brown
    e_s2s = []
    e_b2b = []
    e_s2b = []
    
    for u, v in G.edges():
        b_u = is_bridge[u]
        b_v = is_bridge[v]
        if not b_u and not b_v:
            e_s2s.append((u, v))
        elif b_u and b_v:
            e_b2b.append((u, v))
        else:
            e_s2b.append((u, v))
            
    print(f"Graph constructed: |V| = {G.number_of_nodes()}, |E| = {G.number_of_edges()}")
    print(f"  IoT Sensor Nodes (Blue): {num_nodes - sum(is_bridge)}")
    print(f"  Bridge / Gateway Nodes (Red): {sum(is_bridge)}")
    print(f"  Sensor-to-Sensor links (Green): {len(e_s2s)}")
    print(f"  Bridge-to-Bridge links (Orange): {len(e_b2b)}")
    print(f"  Sensor-to-Bridge links (Brown): {len(e_s2b)}")
    
    return G, positions, is_bridge, e_s2s, e_b2b, e_s2b


def plot_1000_node_topology(
    G, positions, is_bridge, e_s2s, e_b2b, e_s2b,
    output_png="plots/fig_1000_nodes_topology.png",
    output_pdf="plots/fig_1000_nodes_topology.pdf",
    node_labels=("IoT sensor node", "Articulation bridge / Gateway"),
    edge_labels=("Sensor-to-Sensor connection", "Bridge-to-Bridge connection", "Sensor-to-Bridge connection"),
    fig_title="Fig. 2.  Undirected connected graph structure for 1,000-node IoT network",
    dpi=300
):
    fig, ax = plt.subplots(figsize=(8.0, 6.2), dpi=dpi)
    ax.set_facecolor('white')
    fig.patch.set_facecolor('white')
    
    pos = positions
    
    # 1. Draw Edges
    # Edge colors matching the example:
    # Sensor-to-Sensor: Forest green (#1b9e28 or #2e7d32)
    # Bridge-to-Bridge: Bright golden orange (#f59e0b or #f39c12)
    # Sensor-to-Bridge: Brown/Crimson (#8b2500 or #9c27b0 or #a04000)
    
    c_s2s = '#2e7d32'  # Green
    c_b2b = '#f39c12'  # Orange
    c_s2b = '#8b2500'  # Brown
    
    # (a) Sensor-to-Sensor (Green)
    for u, v in e_s2s:
        ax.plot([pos[u][0], pos[v][0]], [pos[u][1], pos[v][1]],
                color=c_s2s, linewidth=0.55, alpha=0.72, zorder=1)
                
    # (b) Bridge-to-Bridge (Orange)
    for u, v in e_b2b:
        ax.plot([pos[u][0], pos[v][0]], [pos[u][1], pos[v][1]],
                color=c_b2b, linewidth=0.85, alpha=0.85, zorder=2)
                
    # (c) Sensor-to-Bridge (Brown)
    for u, v in e_s2b:
        ax.plot([pos[u][0], pos[v][0]], [pos[u][1], pos[v][1]],
                color=c_s2b, linewidth=0.70, alpha=0.78, zorder=2)
                
    # 2. Draw Nodes
    # Blue: Sensor nodes (#0033cc or #0022dd)
    # Red: Bridge/Gateway nodes (#dd0000 or #cc0000)
    c_sensor = '#0033cc'
    c_bridge = '#dd0000'
    
    sensor_nodes = [n for n in G.nodes() if not is_bridge[n]]
    bridge_nodes = [n for n in G.nodes() if is_bridge[n]]
    
    sensor_x = [pos[n][0] for n in sensor_nodes]
    sensor_y = [pos[n][1] for n in sensor_nodes]
    bridge_x = [pos[n][0] for n in bridge_nodes]
    bridge_y = [pos[n][1] for n in bridge_nodes]
    
    # Plot blue sensor nodes
    ax.scatter(sensor_x, sensor_y, c=c_sensor, s=7.0, zorder=3, edgecolors='none')
    # Plot red bridge nodes
    ax.scatter(bridge_x, bridge_y, c=c_bridge, s=12.0, zorder=4, edgecolors='none')
    
    # 3. Create Custom Legend matching the example figure
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', label=node_labels[0],
               markerfacecolor=c_sensor, markersize=6),
        Line2D([0], [0], marker='o', color='w', label=node_labels[1],
               markerfacecolor=c_bridge, markersize=6),
        Line2D([0], [1], color=c_s2s, lw=1.5, label=edge_labels[0]),
        Line2D([0], [1], color=c_b2b, lw=1.5, label=edge_labels[1]),
        Line2D([0], [1], color=c_s2b, lw=1.5, label=edge_labels[2]),
    ]
    
    # Place legend in top-left
    leg = ax.legend(
        handles=legend_elements,
        loc='upper left',
        bbox_to_anchor=(0.04, 0.94),
        frameon=True,
        framealpha=0.92,
        edgecolor='#cbd5e1',
        fontsize=9.2,
        labelspacing=0.45,
        handlelength=1.6,
        handletextpad=0.7,
        borderpad=0.7
    )
    leg.get_frame().set_linewidth(0.8)
    
    ax.axis('off')
    
    # Set tight limits with nice padding
    all_x = [pos[n][0] for n in G.nodes()]
    all_y = [pos[n][1] for n in G.nodes()]
    x_min, x_max = min(all_x), max(all_x)
    y_min, y_max = min(all_y), max(all_y)
    dx = x_max - x_min
    dy = y_max - y_min
    ax.set_xlim(x_min - 0.04 * dx, x_max + 0.04 * dx)
    ax.set_ylim(y_min - 0.04 * dy, y_max + 0.08 * dy)
    
    plt.tight_layout()
    
    # If title/caption requested at bottom
    if fig_title:
        fig.text(0.5, 0.02, fig_title, ha='center', va='bottom', fontsize=11.0, fontfamily='serif')
        plt.subplots_adjust(bottom=0.08)
        
    Path(output_png).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_png, dpi=dpi, bbox_inches='tight', pad_inches=0.1)
    plt.savefig(output_pdf, bbox_inches='tight', pad_inches=0.1)
    plt.close()
    print(f"Saved: {output_png} and {output_pdf}")


if __name__ == "__main__":
    G, pos, is_bridge, e_s2s, e_b2b, e_s2b = generate_1000_node_graph(seed=101)
    
    # Version 1: IoT Network terminology (for this paper)
    plot_1000_node_topology(
        G, pos, is_bridge, e_s2s, e_b2b, e_s2b,
        output_png="plots/fig_1000_nodes_topology_iot.png",
        output_pdf="plots/fig_1000_nodes_topology_iot.pdf",
        node_labels=("IoT sensor node", "Articulation bridge / Gateway"),
        edge_labels=("Sensor-to-Sensor connection", "Bridge-to-Bridge connection", "Sensor-to-Bridge connection"),
        fig_title="Fig. 2.  Undirected connected graph structure for 1,000-node IoT sensor and gateway network"
    )
    
    # Version 2: Exact matching legend to the example (Power bus / EVCS bus) if needed
    plot_1000_node_topology(
        G, pos, is_bridge, e_s2s, e_b2b, e_s2b,
        output_png="plots/fig_1000_nodes_topology_example_style.png",
        output_pdf="plots/fig_1000_nodes_topology_example_style.pdf",
        node_labels=("Power bus", "EVCS bus"),
        edge_labels=("Power-to-Power connection", "EVCS-to-EVCS connection", "Power-to-EVCS connection"),
        fig_title="Fig. 2.  Undirected connected graph structure for power and EVCS nodes"
    )
    
    # Version 3: Pure graph without caption embedded (for LaTeX figure environment inclusion)
    plot_1000_node_topology(
        G, pos, is_bridge, e_s2s, e_b2b, e_s2b,
        output_png="plots/fig_1000_nodes_topology_clean.png",
        output_pdf="plots/fig_1000_nodes_topology_clean.pdf",
        node_labels=("IoT sensor node", "Articulation bridge / Gateway"),
        edge_labels=("Sensor-to-Sensor connection", "Bridge-to-Bridge connection", "Sensor-to-Bridge connection"),
        fig_title=None
    )
