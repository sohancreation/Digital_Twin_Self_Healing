# Telemetry Data Schema

This document specifies the data fields, types, units, and valid domains for `TelemetryRecord`.

---

## Field Specifications

| Field Name | Type | Physical Unit | Valid Range / Allowed Values | Description |
| :--- | :--- | :--- | :--- | :--- |
| `timestamp` | `float` | Seconds ($s$) | $[0.0, \infty)$ | Elapsed simulation time or epoch timestamp |
| `node_id` | `int` | Unitless | $\{0, 1, \dots, N-1\}$ | Unique integer identifier of the transmitting node |
| `packet_rate` | `float` | Packets/sec ($pkt/s$) | $[0.0, \infty)$ | Local packet generation rate |
| `forwarding_rate`| `float` | Packets/sec ($pkt/s$) | $[0.0, \infty)$ | In-transit multi-hop packets forwarded per second |
| `packet_loss` | `float` | Ratio | $[0.0, 1.0]$ | Fraction of lost packets (buffer drop + channel error) |
| `latency` | `float` | Milliseconds ($ms$) | $[0.0, \infty)$ | Average transmission + queuing delay |
| `rssi` | `float` | Decibel-milliwatts ($dBm$) | $[-120.0, -10.0]$ | Received Signal Strength Indicator |
| `energy` | `float` | Percentage ($\%$) | $[0.0, 100.0]$ | Remaining battery percentage |
| `cpu` | `float` | Percentage ($\%$) | $[0.0, 100.0]$ | Microcontroller CPU load |
| `memory` | `float` | Percentage ($\%$) | $[0.0, 100.0]$ | Microcontroller SRAM utilization |
| `neighbor_count`| `int` | Count | $[0, N-1]$ | Active 1-hop wireless neighbors |
| `connection_state`| `str` | Enum | `CONNECTED`, `DEGRADED`, `DISCONNECTED` | Physical / logical link state |
| `routing_state`| `str` | Enum | `IDLE`, `ROUTING`, `CONGESTED` | Queue and routing status |
| `threat_level` | `float` | Normalized | $[0.0, 1.0]$ | Threat score (0.0 = Normal, 1.0 = High Attack) |
| `trust_score` | `float` | Normalized | $[0.0, 1.0]$ | Computed trust score (1.0 = Trusted, 0.0 = Untrusted) |

---

## Data Format Example (CSV row)

```csv
timestamp,node_id,packet_rate,forwarding_rate,packet_loss,latency,rssi,energy,cpu,memory,neighbor_count,connection_state,routing_state,threat_level,trust_score
0.0,0,2.0,0.0,0.0182,23.41,-80.12,99.98,8.60,16.60,2,CONNECTED,IDLE,0.0,1.0
0.0,1,2.0,1.0,0.0210,25.80,-79.80,99.97,10.40,17.40,3,CONNECTED,ROUTING,0.0,1.0
```
