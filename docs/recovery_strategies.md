# Phase 7: Candidate Recovery Strategy Generator

## 1. Overview & Research Objectives

Phase 7 implements the **Candidate Recovery Strategy Generator**, the autonomous decision synthesis module that bridges Phase 6 (Dynamic Risk & Trust Assessment) to Phase 8 (Digital Twin Recovery Simulation & Multi-Objective Optimization).

In an adversarial and resource-constrained IoT mesh/star network, a single hardcoded reaction (such as naive node disconnect) is often catastrophic:
1. **Blind Isolation Induces Network Partition:** Isolating a compromised transit or bridge node (cut vertex) can sever connectivity for dozens of benign leaf nodes, collapsing network delivery ratio to zero.
2. **Resource Exhaustion via Heavy Actuation:** Indiscriminately power-cycling nodes or triggering global routing rebuilds drains scarce battery reserves and introduces multi-second packet blackout intervals.
3. **Sub-Optimal Trade-Offs:** The ideal mitigation depends on attack severity, topology redundancy, node energy reserves, and application criticality.

Phase 7 resolves these challenges by synthesizing a bounded, diverse pool of candidate recovery strategies $\mathcal{S} = \{s_0, s_1, \dots, s_K\}$ whenever the Trust Engine classifies nodes as `SUSPICIOUS` or `QUARANTINED`. Each candidate is strictly typed, parameterized, checked for graph partition feasibility, and costed for downstream Pareto simulation in Phase 8.

---

## 2. Mitigation Action Taxonomy

Phase 7 formalizes a 6-action recovery taxonomy $\mathcal{A}$:

$$\mathcal{A} = \{\text{NO\_ACTION}, \text{RATE\_LIMITING}, \text{DYNAMIC\_REROUTING}, \text{NODE\_ISOLATION}, \text{POWER\_ADJUSTMENT}, \text{NODE\_REBOOT}, \text{COMPOSITE}\}$$

| Action ($\alpha \in \mathcal{A}$) | Target Nodes | Primary Target Threat | Control Parameters | Base Cost ($C_{\text{base}}$) | Est. Latency ($t_{\text{rec}}$) |
| :--- | :---: | :--- | :--- | :---: | :---: |
| **`NO_ACTION`** | $\emptyset$ | Baseline / False Positive | None | $0.0$ | $0.0\,\text{s}$ |
| **`RATE_LIMITING`** | $\{i\}$ | DoS Flooding / Buffer Bloat | `rate_limit_pkts_per_sec` ($2.0$), TokenBucket ($B=10, r=2$) | $1.0$ | $0.5\,\text{s}$ |
| **`DYNAMIC_REROUTING`** | $\{i\}$ | Selective Drop / Blackhole / Congestion | `bypass_routes` ($u \to w \neq i$), `metric_penalty` ($+50$) | $2.5$ | $2.0\,\text{s}$ |
| **`NODE_ISOLATION`** | $\{i\}$ | Sybil / Permanent Malware / Untrusted | `severed_links` ($(u, i) \in E$), `blacklist_duration_s` ($120.0$) | $3.0$ | $1.0\,\text{s}$ |
| **`POWER_ADJUSTMENT`** | Neighbors $\mathcal{N}(i)$ | Partition Prevention / Link Degradation | `power_boost_dbm` ($+4\,\text{dBm}$), `boosted_nodes` | $4.0$ | $1.5\,\text{s}$ |
| **`NODE_REBOOT`** | $\{i\}$ | Volatile Exploit / Frozen State / Buffer Leak | `reboot_duration_s` ($8.0\,\text{s}$), `flush_buffers` (`True`) | $5.0$ | $8.0\,\text{s}$ |
| **`COMPOSITE`** | $\{i\} \cup \mathcal{N}(i)$ | Multi-Threat / Cut-Vertex Bridge Disconnection | `sub_actions` (`[ISO, PWR]` or `[THROTTLE, REROUTE]`) | $4.0 - 5.5$ | $2.0\,\text{s}$ |

### 2.1. Synergistic Composite Mitigation Formulations
In multi-threat scenarios or critical topology bridges, atomic disjoint actions are sub-optimal:
1. **`COMPOSITE_ISOLATE_AND_BRIDGE`:**
   Atomically severs links to target cut vertex $v$ while concurrently instructing surviving neighbors $\mathcal{N}(v)$ to boost transmission power ($+4\,\text{dBm}$). This eliminates the malicious node while actively bridging the topology partition, ensuring $k(G') = 1$ and `is_topology_partitioning = False`.
2. **`COMPOSITE_THROTTLE_AND_REROUTE`:**
   Clamps DoS packet generation via a Token Bucket ($B = 10, r = 2\,\text{pkts/s}$) while immediately diverting incoming transit traffic flows to loop-free bypass routes.

### 2.2. Candidate Cost Modeling
Each candidate strategy $s_k = (\alpha, \mathcal{V}_{\text{target}}, \mathcal{V}_{\text{affected}}, \mathbf{p})$ is assigned an estimated systemic overhead cost $\mathcal{C}(s_k) \in [0.0, 10.0]$:

$$\mathcal{C}(s_k) = \mathcal{C}_{\text{base}}(\alpha) + w_{\text{nodes}} \cdot |\mathcal{V}_{\text{target}}| + w_{\text{affected}} \cdot |\mathcal{V}_{\text{affected}}| + \Delta_{\text{partition}}$$

where $\Delta_{\text{partition}} = +3.0$ if the action induces an unmitigated graph partition.

---

## 3. Topological Feasibility & Graph Partition Avoidance

### 3.1. Cut Vertex (Articulation Point) Theorem
Let $G = (V, E)$ be the connected undirected graph representing the Digital Twin active topology. 
A node $v \in V$ is an **articulation point** if the induced subgraph $G[V \setminus \{v\}]$ has strictly more connected components than $G$:

$$k(G[V \setminus \{v\}]) > k(G)$$

**Theorem (Partition Hazard of Naive Isolation):**
If $v \in \text{CutVertices}(G)$ and $v$ is isolated via link removal $\forall (u, v) \in E$, then there exist at least two benign nodes $u_1, u_2 \in V \setminus \{v\}$ such that no path exists between $u_1$ and $u_2$ in $G' = (V \setminus \{v\}, E \setminus \{(u, v)\})$.

### 3.2. Feasibility Evaluation Pipeline
The `FeasibilityChecker` evaluates every proposed candidate before inclusion into the strategy pool:
1. **Partition Detection (`check_isolation_partition`):**
   Simulates node removal on a copy of $G$. If $k(G') > 1$, the candidate is tagged with `is_topology_partitioning = True`.
2. **Path Stretch & Hop Latency Budget (`evaluate_path_stretch`):**
   Computes the increase in hop count $\Delta h = \text{len}(P_{\text{bypass}}) - \text{len}(P_{\text{orig}})$. If $\Delta h > 3$, the candidate is flagged for excessive delay.
3. **Neighbor Congestion Headroom (`check_neighbor_congestion`):**
   Verifies that alternate bypass neighbors have sufficient CPU headroom ($< 80\%$) and low packet loss ($< 20\%$) to absorb redirected flows.
4. **Power Boost Feasibility (`check_power_boost_feasibility`):**
   Verifies that neighboring nodes possess sufficient residual battery energy ($E_j > 20\%$).

---

## 4. Candidate Strategy Generator Architecture

The `CandidateStrategyGenerator` coordinates candidate synthesis:

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                           INPUT CONTEXT                                 │
│  • Digital Twin Graph Shadow G = (V, E)                                 │
│  • Node States from Phase 6 (TRUSTED, SUSPICIOUS, QUARANTINED)          │
│  • Criticality Scores C_i and Risk Scores R_i                           │
│  • Instantaneous ML Attack Classifiers & Anomaly Vectors                │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                 CandidateStrategyGenerator.generate_pool()              │
│                                                                         │
│  1. Baseline Candidate: Always insert s_0 = NO_ACTION                   │
│  2. For each node i in QUARANTINED:                                    │
│     ├── Build NODE_ISOLATION (Tag partition hazard if cut vertex)       │
│     ├── If partition hazard detected:                                   │
│     │   └── Pair with neighbor POWER_ADJUSTMENT bridge candidate       │
│     ├── Build DYNAMIC_REROUTING (Compute loop-free bypass paths)       │
│     └── Build NODE_REBOOT (Soft power cycle with buffer flush)          │
│  3. For each node j in SUSPICIOUS:                                      │
│     ├── Build RATE_LIMITING (Throttle to 2.0 pkts/s)                    │
│     └── Build DYNAMIC_REROUTING (Proactive deprioritization)            │
│  4. Feasibility Pruning & StrategyPool Assembly (Bounded to K <= 8)     │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              STRATEGY POOL S = {s_0, s_1, ..., s_K}                     │
│  Forwarded to Phase 8 Digital Twin Simulation & Pareto Optimization     │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.1. Algorithmic Complexity
The candidate generator operates with worst-case computational complexity:

$$\mathcal{O}(|V_{\text{target}}| \cdot (|V| + |E|))$$

Given that IoT networks typically exhibit $|V| \le 100$ and the number of simultaneous target nodes $|V_{\text{target}}| \le 5$, generation executes in **microseconds**, ensuring viability for embedded edge gateways and microcontrollers.

---

## 5. Experimental Validation & Results

Phase 7 was experimentally validated via `scripts/run_phase7_recovery_candidate_experiments.py` against the multi-attack network trace generated in Phases 3 and 6.

### 5.1. Strategy Pool Diversity Across Decision Epochs

| Epoch ($t$) | Trigger Context | Nodes Flagged | Generated Pool Size ($|\mathcal{S}|$) | Partition Hazard Flagged? | Generation Latency |
| :---: | :--- | :---: | :---: | :---: | :---: |
| **$50.0\,\text{s}$** | DoS Onset | Node 2 (`SUSP`), Node 5 (`SUSP`) | **3 candidates** | No (`False`) | **$127.6\,\mu\text{s}$** |
| **$70.0\,\text{s}$** | Selective Drop Peak | Node 3 (`QUAR`), Node 5 (`QUAR`), Node 2 (`SUSP`) | **8 candidates** | **Yes (Node 3 & Node 5)** | **$447.8\,\mu\text{s}$** |
| **$95.0\,\text{s}$** | Multi-Attack Overlap | Node 3 (`QUAR`), Node 4 (`QUAR`), Node 5 (`QUAR`) | **8 candidates** | **Yes (Node 3, 4, 5)** | **$245.3\,\mu\text{s}$** |
| **$115.0\,\text{s}$** | Recovery / Evasion | Node 3 (`QUAR`), Node 4 (`QUAR`), Node 5 (`SUSP`) | **8 candidates** | **Yes (Node 3 & Node 4)** | **$196.1\,\mu\text{s}$** |

### 5.2. Scalability & Execution Latency Benchmark
The generator was evaluated across varying network topologies ($N \in \{6, 10, 16, 25\}$ nodes) over 100 repeated trials per scale:

| Network Scale ($|V|$) | Mean Latency ($\mu\text{s}$) | P95 Latency ($\mu\text{s}$) | Candidates Generated | Real-Time Feasible? |
| :---: | :---: | :---: | :---: | :---: |
| **6 Nodes** (Baseline) | **$52.49\,\mu\text{s}$** | $59.49\,\mu\text{s}$ | 7 | **Yes ($< 0.1\,\text{ms}$)** |
| **10 Nodes** | **$57.06\,\mu\text{s}$** | $61.97\,\mu\text{s}$ | 7 | **Yes ($< 0.1\,\text{ms}$)** |
| **16 Nodes** | **$50.73\,\mu\text{s}$** | $52.70\,\mu\text{s}$ | 7 | **Yes ($< 0.1\,\text{ms}$)** |
| **25 Nodes** | **$51.30\,\mu\text{s}$** | $55.71\,\mu\text{s}$ | 7 | **Yes ($< 0.1\,\text{ms}$)** |

**Key Finding:** Latency remains virtually constant (~$50 - 57\,\mu\text{s}$) because candidate exploration is strictly bounded by the number of suspicious/quarantined nodes and local neighborhood checks, scaling comfortably to resource-constrained IoT gateways.

---

## 6. Generated Visualizations (300 DPI)

1. **`phase7_plot1_mitigation_taxonomy.png`**:
   Comprehensive hierarchical breakdown of the 6 recovery action classes, their operational mechanisms, trigger conditions, parameters, and normalized cost vectors.
2. **`phase7_plot2_candidate_pool_diversity.png`**:
   Distribution of mitigation action types generated across key simulation epochs ($t = 50\text{s}, 70\text{s}, 95\text{s}, 115\text{s}$), highlighting dynamic adaptation to attack progression.
3. **`phase7_plot3_partition_avoidance_graph.png`**:
   Graph topology visualization showing the network partition resulting from naive isolation of cut vertex Node 3, juxtaposed with the self-healing power-boost bridge established between neighbor nodes.
4. **`phase7_plot4_candidate_generation_latency.png`**:
   Latency distribution across network scales ($N = 6, 10, 16, 25$), proving ultra-fast microsecond execution ($\mu < 60\,\mu\text{s}$).
5. **`phase7_plot5_action_cost_vs_impact.png`**:
   Cost versus expected recovery time trade-off space for all candidate actions, illustrating Pareto frontiers for Phase 8 multi-objective selection.

---

## 7. Artifact Ledger

- **Core Module:** `backend/recovery/`
  - `models.py`: Data schemas (`RecoveryActionType`, `RecoveryCandidate`, `StrategyPool`, `RecoveryConfig`).
  - `feasibility.py`: `FeasibilityChecker` (cut-vertex partition detection, loop-free alternate path search, battery reserves check).
  - `taxonomy.py`: Parameterized candidate builders for all 6 recovery actions.
  - `generator.py`: `CandidateStrategyGenerator` orchestrating candidate synthesis.
  - `__init__.py`: Package exports.
- **Automated Tests:** `tests/test_recovery.py` (10 unit test cases, 100% pass rate; total project suite: 134/134 passing).
- **Experiment Script:** `scripts/run_phase7_recovery_candidate_experiments.py`.
- **Results:** `results/phase7_recovery_candidate_summary.json`.
