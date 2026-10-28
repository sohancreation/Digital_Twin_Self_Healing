# Digital Twin State Synchronizer & Shadow Model (Phase 2)

This document formalizes the Digital Twin architecture, state representation, synchronization semantics, history management, and health models implemented in Phase 2.

---

## 1. Digital Twin Definition in this Framework

In this research framework, the **Digital Twin (DT)** is defined as a living, synchronized computational model of the resource-constrained IoT network.

At Phase 2, the Digital Twin functions as a **State Synchronization and Shadow Modeling Layer**:
* **Mirroring:** Ingests incoming `TelemetryRecord` streams and maintains exact virtual shadow states for individual nodes and links.
* **Temporal Tracking:** Bounded, time-windowed history buffers enable retrospective multi-metric queries.
* **Topology Shadow:** Replicates active connectivity graphs, neighbor relationships, and directional link states.
* **Macroscopic Health Summarization:** Provides rule-based, transparent aggregation of network availability and resource health without unverified heuristic weighting.

> [!NOTE]
> At Phase 2, the Digital Twin is **not yet** a predictive, attack-detecting, or self-healing engine. These capabilities will be developed on top of this verified foundation in Phases 5–9.

---

## 2. Digital Twin Data Models

### 2.1 Virtual Node State (`TwinNodeState`)
Maintains the latest verified physical, channel, and computational state of an individual IoT node:
* `node_id`: Unique integer identifier.
* `timestamp`: Telemetry epoch timestamp (seconds).
* `position`: Continuous 2D spatial coordinate $(x, y)$.
* `packet_rate`: Generated traffic rate ($pkt/s$).
* `forwarding_rate`: In-transit forwarding rate ($pkt/s$).
* `packet_loss`: Combined packet loss ratio $[0.0, 1.0]$.
* `latency`: End-to-end / queuing latency ($ms$).
* `rssi`: Received signal strength indicator ($dBm$).
* `energy`: Remaining battery percentage $[0.0, 100.0]$.
* `cpu`: CPU utilization percentage $[0.0, 100.0]$.
* `memory`: SRAM buffer utilization percentage $[0.0, 100.0]$.
* `neighbor_count`: Active 1-hop wireless neighbor count.
* `connection_state`: Enum (`CONNECTED`, `DEGRADED`, `DISCONNECTED`).
* `routing_state`: Enum (`IDLE`, `ROUTING`, `CONGESTED`).
* `threat_level`: Ingested threat level (0.0 for baseline).
* `trust_score`: Ingested trust score (1.0 for baseline).

### 2.2 Link State (`LinkState`)
Virtual representation of directed wireless links between adjacent nodes:
* `source_node`, `target_node`: Directed link endpoint identifiers.
* `estimated_rssi`: Telemetry-derived link signal strength.
* `estimated_latency`: Reported transmission + propagation delay.
* `estimated_loss`: Channel error probability.
* `active`: Boolean indicating whether both link endpoints are active and connected.

### 2.3 Network-Level Twin State (`NetworkTwinState`)
Macroscopic aggregation across all synchronized nodes:
* `node_count`, `active_node_count`, `connected_node_count`.
* `average_packet_loss`, `average_latency`, `average_rssi`, `average_cpu`, `average_memory`.
* `total_energy`, `network_availability`.

---

## 3. Synchronization Mechanism

```
[IoT Physical / Simulator Node]
             │
             │ Emits TelemetryRecord
             ▼
[DigitalTwinSynchronizer]
             │ 1. Records Ingestion Timestamp (Wall-clock perf_counter)
             │ 2. Validates Payload Schema & Physical Bounds
             │ 3. Computes Software Sync Latency: (t_ingest_end - t_ingest_start)
             │ 4. Converts to TwinNodeState & SyncMetadata
             ▼
[DigitalTwin Core]
             ├── Apply Node State -> update node_states[node_id]
             ├── Ingest to HistoryManager -> time-windowed bounded deque
             ├── Update NetworkTopologyModel -> synchronize edges and LinkStates
             └── Recompute NetworkTwinState & NetworkHealthSummary
```

### Synchronization Latency Definition
* **Software Ingestion Synchronization Latency:**  
  $$\Delta t_{\text{sync}} = t_{\text{ingest\_end}} - t_{\text{ingest\_start}} \quad (\text{measured in milliseconds via } \texttt{time.perf\_counter()})$$
* This reflects the internal software processing and state validation overhead of the Digital Twin platform. It is strictly distinguished from wireless physical transmission latency.

---

## 4. Bounded History Mechanism

To ensure suitability for resource-constrained edge gateways and reproducible academic research, historical telemetry is stored in bounded deques:
* Configurable retention window $W_{\text{history}}$ (default: $60.0\text{ seconds}$).
* Automatic eviction: Records with $\text{timestamp} < (\text{latest\_timestamp} - W_{\text{history}})$ are pruned.
* Supported query APIs:
  * `get_node_history(node_id, window_seconds)`
  * `get_metric_history(node_id, metric, window_seconds)`
  * `get_network_history(metric, window_seconds)`
  * `get_recent_state(node_id, seconds)`

---

## 5. Descriptive Health Assessment

The health model in `backend/digital_twin/health.py` evaluates network status using transparent physical thresholds:
* **`HEALTHY`**: Connected node ratio $\ge 0.90$, average packet loss $< 0.10$, and 0 degraded nodes.
* **`DEGRADED`**: Connected node ratio $\ge 0.50$ and average packet loss $< 0.40$, or active degraded nodes present.
* **`CRITICAL`**: Connected node ratio $< 0.50$ or average packet loss $\ge 0.40$.

---

## 6. Assumptions & Known Limitations

1. **In-Memory Storage:** Phase 2 stores state in-memory inside the Python runtime rather than an external time-series database (e.g. InfluxDB/TimescaleDB).
2. **Deterministic Single-Threaded Ingestion:** Telemetry is processed synchronously in simulation experiments. Multi-threaded / async queuing will be evaluated when network I/O is introduced.
3. **No Attack Predictions Yet:** Threat scores and trust values directly mirror ingested inputs and will remain nominal until Phase 5 (ML Detection) and Phase 6 (Risk Engine).
