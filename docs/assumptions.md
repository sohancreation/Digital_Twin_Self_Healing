# Research Assumptions (Phase 1 Baseline)

This document formalizes the mathematical, computational, physical, and network assumptions governing the Phase 1 IoT Network Simulator.

> [!NOTE]
> All items listed below are explicit theoretical and modeling assumptions. They serve as controlled experimental parameters and are not presented as empirically measured physical ground truths.

---

## 1. Network Topology & Spatial Layout Model
* **Coordinate System:** 2D Euclidean continuous plane $[0, X_{\max}] \times [0, Y_{\max}]$.
* **Topology Types:**
  * **Grid (Baseline):** Regular $R \times C$ lattice with horizontal and vertical nearest-neighbor connectivity.
  * **Random:** Uniform spatial distribution $\mathbf{p}_i \sim \mathcal{U}([0, X_{\max}] \times [0, Y_{\max}])$ with minimum-distance bridging to ensure graph connectivity.
  * **Mesh:** Circular arrangement with high inter-node degree within communication radius.
  * **Ring:** Circular arrangement with adjacent 2-neighbor periodic connectivity.
  * **Star:** Central coordinator (Node 0) with $N-1$ peripheral leaf nodes.
* **Link Symmetry:** Wireless channels are assumed symmetric in topology establishment: if $d(u, v) \le R_{\text{comm}}$, then $(u, v) \in E \iff (v, u) \in E$.

---

## 2. Wireless Channel & Propagation Model
* **Log-Distance Path Loss with Shadowing:**
  $$\text{RSSI}(d) = \text{RSSI}_0 - 10 \eta \log_{10}\left(\frac{\max(d, d_0)}{d_0}\right) + X_\sigma$$
  * $\text{RSSI}_0 = -30.0\text{ dBm}$ (Reference received power at $d_0 = 1.0\text{ m}$)
  * $\eta = 2.8$ (Path loss exponent corresponding to suburban / light industrial environments)
  * $X_\sigma \sim \mathcal{N}(0, \sigma^2)$ with $\sigma = 2.0\text{ dB}$ (Log-normal shadow fading)
  * Bounds: $\text{RSSI} \in [-120\text{ dBm}, -10\text{ dBm}]$ (Hardware sensitivity floor to receiver saturation)
* **Channel-Induced Packet Error Rate:**
  $$P_{\text{loss, channel}} = \frac{1}{1 + \exp\left(0.2 \cdot (\text{RSSI} - \text{RSSI}_{\text{threshold}})\right)}, \quad \text{where } \text{RSSI}_{\text{threshold}} = -100\text{ dBm}$$

---

## 3. Traffic Generation & Queuing Model
* **Packet Arrival:** In baseline normal operation, locally generated traffic follows a discrete Gaussian approximation of a Poisson process:
  $$\lambda_i(t) \sim \max(0, \mathcal{N}(\mu_\lambda, \sigma_\lambda^2)), \quad \mu_\lambda = 2.0\text{ pkts/s}, \sigma_\lambda = 0.4\text{ pkts/s}$$
* **Queuing & Buffer Overflow:**
  * First-In First-Out (FIFO) queue with capacity $Q_{\max} = 50$ packets.
  * Drop-tail buffer overflow occurs if new packets exceed available capacity:
    $$P_{\text{loss, buffer}} = \frac{\max(0, N_{\text{new}} - (Q_{\max} - Q_{\text{len}}))}{N_{\text{new}}}$$
  * Combined Packet Loss:
    $$P_{\text{loss}} = P_{\text{loss, buffer}} + (1 - P_{\text{loss, buffer}}) P_{\text{loss, channel}}$$

---

## 4. Latency Model
* **End-to-End Latency Formulation:**
  $$T_{\text{latency}} = T_{\text{base}} + T_{\text{queue}} + T_{\text{traffic}}$$
  * $T_{\text{base}} \sim \mathcal{N}(18\text{ ms}, 2\text{ ms})$ (Radio preamble, modulation, and propagation delay)
  * $T_{\text{queue}} = \frac{Q_{\text{len}}}{Q_{\max}} \times 40\text{ ms}$ (Queuing delay)
  * $T_{\text{traffic}} = \frac{N_{\text{traffic}}}{2 \mu_\lambda} \times 12\text{ ms}$ (Channel contention delay)

---

## 5. Computational Resource Models (CPU & Memory)
* **Resource-Constrained Embedded Profile (ESP32-class MCU):**
  * **CPU Utilization:**
    $$\text{CPU}(t) = \min\left(100\%, \text{CPU}_{\text{base}} + \alpha_{\text{cpu}} (\lambda_{\text{gen}} + \lambda_{\text{fwd}}) + \epsilon_{\text{cpu}}\right)$$
    with $\text{CPU}_{\text{base}} = 5.0\%$, $\alpha_{\text{cpu}} = 1.8\%\text{ per pkt/s}$, $\epsilon_{\text{cpu}} \sim \mathcal{N}(0, 0.5^2)$.
  * **Memory Utilization:**
    $$\text{Mem}(t) = \min\left(100\%, \text{Mem}_{\text{base}} + \frac{Q_{\text{len}}}{Q_{\max}} \cdot 42.5\% + \beta_{\text{mem}} N_{\text{new}} + \epsilon_{\text{mem}}\right)$$
    with $\text{Mem}_{\text{base}} = 15.0\%$, $\beta_{\text{mem}} = 0.8\%$, $\epsilon_{\text{mem}} \sim \mathcal{N}(0, 0.3^2)$.

---

## 6. Energy Depletion Model
* **Discrete-Time Energy Drain:**
  $$E(t + \Delta t) = \max\left(0, E(t) - \left[P_{\text{idle}} \Delta t + E_{\text{tx}} N_{\text{tx}} + E_{\text{rx}} N_{\text{rx}}\right]\right)$$
  * $E_{\text{initial}} = E_{\max} = 1000.0\text{ Joules}$
  * $P_{\text{idle}} = 0.015\text{ W}$ ($15\text{ mW}$ quiescent draw in active listen)
  * $E_{\text{tx}} = 0.008\text{ J/packet}$ ($8\text{ mJ}$ per transmission at $+14\text{ dBm}$)
  * $E_{\text{rx}} = 0.004\text{ J/packet}$ ($4\text{ mJ}$ per packet reception and processing)
* **Exhaustion State:** If $E(t) \le 0$, node transitions permanently to `DISCONNECTED` state ($P_{\text{loss}} = 1.0$, traffic $= 0$, CPU $= 0$, Memory $= 0$).

---

## 7. Simulation Timing & Determinism
* **Time Resolution:** Fixed discrete step $\Delta t = 1.0\text{ s}$.
* **Pseudo-Random Number Generation:** NumPy `Generator` initialized with explicit integer seeds (default: `seed = 42`).
* **Reproducibility Guarantee:** All stochastic variables (packet rates, channel noise, jitter) are strictly tied to the configured RNG generator. Identical seeds produce bit-identical telemetry outputs.
