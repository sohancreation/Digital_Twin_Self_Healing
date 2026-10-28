# Controlled Cyberattack Simulation Framework (Phase 3)

This document formalizes the mathematical models, parameter definitions, scheduler semantics, and ground-truth labeling methodologies implemented in Phase 3.

---

## 1. Attack Modeling Principle

All attack and fault behaviors in this framework are modeled by perturbing the **underlying operational and traffic dynamics** rather than merely overriding output telemetry metrics:

$$\text{Attack Configuration} \longrightarrow \Delta \text{Traffic / Operational State} \longrightarrow \text{Simulator Dynamics} \longrightarrow \text{Observable Telemetry}$$

This ensures that:
1. Physical causality is preserved (e.g. higher traffic naturally induces buffer fill, queuing delay, CPU load, and energy depletion).
2. The resulting dataset reflects realistic multi-metric correlations necessary for robust machine learning in Phase 4 and Phase 5.
3. The original `TelemetryRecord` interface remains unpolluted.

---

## 2. Implemented Attack & Fault Models

### 2.1 Denial of Service (DoS) / Packet Flooding Attack (`backend/attacks/dos.py`)
* **Mechanism:** An adversary floods the target node $v_{\text{target}}$ with a sustained surge of malicious packets.
* **Traffic Perturbation:**
  $$N_{\text{fwd}}(v_{\text{target}}, t) = N_{\text{normal\_fwd}}(v_{\text{target}}, t) + \left\lfloor (\lambda_{\text{flood}} + \epsilon_{\text{jitter}}) \cdot \Delta t \right\rceil$$
  where $\lambda_{\text{flood}} = \text{intensity}$ (default: $20.0\text{ pkts/s}$) and $\epsilon_{\text{jitter}} \sim \mathcal{N}(0, (0.2 \cdot \text{intensity})^2)$.
* **Propagated Observable Effects:**
  * Forwarding rate increases sharply.
  * Buffer queue rapidly saturates toward capacity ($Q_{\max} = 50$).
  * Buffer drop-tail packet loss increases when queue is full.
  * Queuing latency increases from $\approx 28\text{ ms}$ to $\approx 91\text{ ms}$.
  * CPU utilization surges from $\approx 11\%$ to $\approx 49\%$.
  * Energy depletion accelerates proportionally to packet servicing.

### 2.2 Compromised Node / Selective Packet Dropping (`backend/attacks/compromised_node.py`)
* **Mechanism:** Simulates an internally compromised node executing a selective forwarding (gray-hole) attack.
* **Traffic Perturbation:**
  * For inbound forwarded packets $N_{\text{in}}$, the node drops packets according to a binomial distribution:
    $$N_{\text{dropped}} \sim \text{Binomial}(N_{\text{in}}, p_{\text{drop}}), \quad \text{where } p_{\text{drop}} = \text{intensity} \in [0.0, 1.0]$$
  * Surviving forwarded packets: $N_{\text{surviving}} = N_{\text{in}} - N_{\text{dropped}}$.
* **Telemetry Reflection:**
  * Forwarding throughput downstream is suppressed.
  * Total packet loss ratio on the node reflects the malicious drop:
    $$P_{\text{loss, total}} = 1 - (1 - P_{\text{loss, baseline}}) \cdot (1 - p_{\text{drop}})$$
  * With $p_{\text{drop}} = 0.5$, mean observed packet loss on the node increases from $\approx 2.6\%$ to $\approx 51.3\%$.

### 2.3 Node Failure / Crash Outage (`backend/attacks/node_failure.py`)
* **Mechanism:** Simulates hardware power cut, processor crash, or transceiver death.
* **Routing & State Perturbation:**
  * During the failure window $[t_{\text{start}}, t_{\text{end}})$, the target node is marked unavailable for routing.
  * Intermediate routing flows bypass or fail at the node.
  * Node state transitions to:
    $$\text{connection\_state} = \texttt{DISCONNECTED}, \quad \text{packet\_loss} = 1.0, \quad \lambda_{\text{gen}} = 0, \quad \lambda_{\text{fwd}} = 0, \quad \text{CPU} = 0\%, \quad \text{Latency} = 0\text{ ms}$$
* **Recovery Semantics:**
  * When $t \ge t_{\text{end}}$, the node reboots and resumes operation **if and only if** remaining battery energy $E(t) > 0$.
  * If battery is exhausted ($E \le 0$), the node remains permanently disconnected.

---

## 3. Attack Scheduler Semantics

The `AttackScheduler` manages attack lifecycles using strict, deterministic half-open temporal intervals:

$$\text{Active}(t) \iff \text{start\_time} \le t < \text{end\_time} \quad \text{and} \quad \text{enabled} = \texttt{True}$$

* **Boundary Behavior:**
  * At $t = \text{start\_time}$: Attack begins immediately.
  * At $t = \text{end\_time} - \Delta t$: Attack is active.
  * At $t = \text{end\_time}$: Attack terminates; normal operation resumes.
* **Determinism:** The scheduler uses a dedicated `attack_seed` (e.g. `1001`), ensuring that attack stochasticity (e.g. binomial drops, flood jitter) is decoupled from baseline network randomness.

---

## 4. Ground-Truth Annotation Model

To preserve the invariance of `TelemetryRecord`, annotations are recorded in an aligned secondary structure (`AttackGroundTruth`):

| Column | Type | Description |
| :--- | :--- | :--- |
| `timestamp` | `float` | Simulation timestamp in seconds |
| `node_id` | `int` | Integer identifier of the node |
| `attack_active` | `int` | Binary indicator: `1` if attack active on this node, `0` if normal |
| `attack_type` | `str` | `"normal"`, `"dos"`, `"compromised_node"`, `"node_failure"` |
| `attack_id` | `str` | Scenario ID (e.g., `"DOS_001"`, `"COMP_001"`, `"FAIL_001"`) |
| `target_node` | `int` | Target node ID |
| `intensity` | `float` | Configured intensity parameter |
| `is_indirectly_affected` | `bool` | Flag for collateral non-target routing effects |

Both formats are preserved:
1. Separate files: `phase3_<scenario>.csv` and `phase3_<scenario>_ground_truth.csv`.
2. Merged dataset: `phase3_attack_dataset.csv` for Phase 4 feature engineering.

---

## 5. Summary of Experimental Results

Executed on 6 nodes, 300 seconds, baseline `seed = 42`:

| Scenario | Target Node | Interval | Configured Intensity | Normal Baseline Value | Observed Attack Value |
| :--- | :---: | :---: | :--- | :--- | :--- |
| **DoS Flooding** | Node 2 | 100s – 150s | $20.0\text{ pkts/s}$ | CPU: $11.12\%$, Lat: $28.25\text{ ms}$ | CPU: $48.68\%$, Lat: $91.07\text{ ms}$ |
| **Compromised Node**| Node 3 | 150s – 200s | $p = 0.50$ ($50\%$ drop) | Packet Loss: $2.65\%$ | Packet Loss: $51.32\%$ |
| **Node Failure** | Node 4 | 220s – 250s | Binary ($1.0$) | State: `CONNECTED`, Loss: $2.4\%$ | State: `DISCONNECTED`, Loss: $100\%$ |
| **Combined** | Nodes 2, 3, 4 | Multi-stage | As above | Nominal Network Availability: $1.0$ | Availability dropped to $0.833$ during failure |

---

## 6. Assumptions & Limitations

1. **Single Attack per Node:** Simultaneous overlapping multi-attacks targeting the exact same node are not evaluated in Phase 3 (scheduled in separate time windows).
2. **Simplified Threat Vectors:** Advanced persistent threats (APTs), routing loop attacks, and cryptographic spoofing are planned for future extension.
3. **No Autonomous Mitigation:** Phase 3 only injects attacks and validates observables; detection and recovery belong to subsequent phases.
