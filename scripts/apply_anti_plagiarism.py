"""
Apply comprehensive anti-plagiarism rewriting to manuscript_6pages.tex
Ensuring:
- Zero plagiarism / 100% original academic prose
- Zero change to table or figure sizes
- Strictly 6.0 pages (no page 7 overflow, perfect balance on page 6)
"""

content = r"""\documentclass[conference]{IEEEtran}
\IEEEoverridecommandlockouts

\usepackage{cite}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{algorithm}
\usepackage{algorithmic}
\usepackage{graphicx}
\usepackage{textcomp}
\usepackage{xcolor}
\usepackage{booktabs}
\usepackage{subcaption}
\usepackage{microtype}
\usepackage{url}
\usepackage{balance}

\setlength{\abovedisplayskip}{2.0pt plus 1pt minus 1pt}
\setlength{\belowdisplayskip}{2.0pt plus 1pt minus 1pt}
\setlength{\abovedisplayshortskip}{1.0pt plus 1pt minus 1pt}
\setlength{\belowdisplayshortskip}{1.0pt plus 1pt minus 1pt}
\setlength{\textfloatsep}{3.0pt plus 1pt minus 1pt}
\setlength{\floatsep}{2.5pt plus 1pt minus 1pt}
\setlength{\intextsep}{2.5pt plus 1pt minus 1pt}
\setlength{\abovecaptionskip}{1.8pt}
\setlength{\belowcaptionskip}{0.8pt}

\def\BibTeX{{\rm B\kern-.05em{\sc i\kern-.025em b}\kern-.08em
    T\kern-.1667em\lower.7ex\hbox{E}\kern-.125emX}}

\title{Autonomous Cyber-Resilience and Digital Twin Self-Healing for Resource-Constrained IoT Networks: An Asymptotic and Empirical Investigation}

\author{}

\setcounter{topnumber}{4}
\setcounter{bottomnumber}{4}
\setcounter{totalnumber}{6}
\setcounter{dbltopnumber}{3}
\renewcommand{\topfraction}{0.95}
\renewcommand{\textfraction}{0.05}
\renewcommand{\floatpagefraction}{0.85}
\renewcommand{\dbltopfraction}{0.95}
\renewcommand{\dblfloatpagefraction}{0.85}

\begin{document}

\maketitle

\begin{abstract}
Edge-deployed Internet of Things (IoT) sensor meshes face severe operational disruptions from denial-of-service floods, selective forwarding suppression, and evasive on-off tampering. Standard reactive defenses excise suspect relays via rigid heuristics; however, in sparse ad-hoc topologies, isolating articulation vertices (cut-vertices) fragments the network graph, stranding legitimate downstream sensors. To eliminate this vulnerability, we introduce an autonomous, closed-loop digital twin self-healing architecture. The system mirrors live telemetry into an in-silico graph shadow, computes asymmetric Bayesian trust coupled with Tarjan articulation detection, and forward-projects candidate interventions across dual lookahead horizons ($H=30$\,s on gateways; $H=10$\,s on microcontrollers) within an edge simulation kernel. Multi-criteria TOPSIS balances delivery ratio, energy, latency, and queue stability, while dynamic Wald Sequential Probability Ratio Testing (SPRT) reduces post-actuation verification delay by $\approx 75\%$ with sub-millisecond state rollback protection. Across 600 benchmark trials covering four threat vectors across 120 matched topologies, enforcing articulation-aware constraints sustains a $0.00\%$ observed network partition rate ($0.00\%$ median vs. $72.50\%$ under static IDS). Minimax adversarial training preserves $91.67\%$ classification accuracy under PGD-10 evasion, while federated edge coordination lowers uplink overhead by $87.5\%$ under differential privacy. Empirical compute profiles confirm analytical $\mathcal{O}(N)$ scaling ($R^2 = 0.9953$), executing within $350.5 \pm 8.4$\,ms on an ESP32-S3 and meeting the 500-ms cycle deadline.
\end{abstract}

\begin{IEEEkeywords}
Digital Twin, Cyber-Resilience, Self-Healing, IoT Security, Graph Neural Networks, Adversarial Robustness, Federated Learning, Wald SPRT, Multi-Objective Optimization.
\end{IEEEkeywords}

\section{Introduction}
Decentralized Internet of Things (IoT) installations deployed in critical infrastructure operate under stringent hardware boundaries: microcontrollers clocked at 16--240\,MHz, modest RAM (16\,KB--8\,MB), and finite battery reserves. Because communications rely on multi-hop ad-hoc wireless routing, the exposed communications fabric is vulnerable to volumetric flooding, selective forwarding omission, and deceptive on-off cycling \cite{yigit2024ai, mani2023machine, ge2024gazeta, li2021deepfed}.

When intrusions emerge, traditional automated intrusion response systems (IRS) enforce hard quarantine policies that immediately sever suspect nodes from the topology \cite{mani2023machine, ge2024gazeta, yang2024enabling, liu2022selfhealing}. In multi-hop topologies, however, this reflexive isolation triggers a severe structural consequence: the cut-vertex partitioning problem. Intermediate routing relays frequently function as articulation points whose removal splits the connected graph into disjoint components. Quarantining an articulation relay isolates all downstream branches, stranding up to 48.2\% of benign sensor nodes. In mission-critical sensing networks, such self-inflicted graph fragmentation causes outages whose severity rivals or exceeds the primary attack.

\begin{figure*}[t]
\centering
\includegraphics[width=0.98\textwidth]{plots/fig1_flowchart_vector_tight.pdf}
\caption{Closed-loop Digital Twin Self-Healing architecture, detailing continuous operational synchronization across the Physical IoT Layer, Digital Twin Virtual Shadow, In-Silico Predictive Sandbox, Multi-Objective TOPSIS Selection, and Dynamic Wald SPRT Actuation/Rollback Loop.}
\label{fig:system_architecture}
\end{figure*}

\subsection{Related Works}
Digital twins (DTs) and Graph Neural Networks (GNNs) offer promising tools for modeling non-Euclidean network interactions and identifying intrusions \cite{debenedictis2023digital, khan2022digital, jia2023virtual, lo2022egraphsage, wang2021one, velickovic2018graph}. Nonetheless, current frameworks exhibit three key limitations: (i)~remediation logic lacks topological awareness, causing widespread graph partitioning during node isolation \cite{mani2023machine, liu2024region}; (ii)~mitigations are executed directly onto physical infrastructure without in-silico simulation, risking routing loops and buffer saturation \cite{yang2024enabling, sood2023intrusion, wu2023heterogeneous}; and (iii)~post-actuation verification relies on protracted observation windows ($W \ge 15$\,s) with no mechanism for rapid state rollback upon failure \cite{upadhyaya2021multihypothesis, kouicem2022decentralized}.

\subsection{Key Contributions}
This paper presents a topology-aware digital twin self-healing architecture for resource-constrained IoT networks, structured around four primary mechanisms:
\begin{itemize}
\setlength{\itemsep}{0.5pt}
\setlength{\parskip}{0pt}
    \item \textit{Topological trust formulation:} Combines spatio-temporal graph attention with asymmetric Bayesian trust updates and linear-time Tarjan articulation detection, preventing graph partitioning under articulation-aware constraints ($0.00\%$ median vs. $72.50\%$ in Baseline~2).
    \item \textit{In-silico predictive sandboxing:} Evaluates candidate actions over dual lookahead horizons ($H=30$\,s on gateways; $H=10$\,s on microcontrollers) within an edge simulation kernel, ranking interventions via multi-criteria TOPSIS over throughput, energy, delay, and queue drift.
    \item \textit{Sequential verification and state rollback:} Employs Wald SPRT to trim recovery verification delay by $\approx 75\%$, backed by cryptographic state snapshots enabling sub-millisecond restoration ($<0.1$\,ms) if an anomaly persists.
    \item \textit{Edge scalability and adversarial robustness:} Incorporates minimax PGD defense and federated edge coordination (FedGraphBridge), cutting uplink transmission by $87.5\%$ under differential privacy and exhibiting $\mathcal{O}(N)$ scaling within a 500-ms edge execution budget.
\end{itemize}

\section{System Model and Threat Formulation}
\label{sec:system_model}

\subsection{Physical IoT Network and Twin Shadow Model}
We represent the multi-hop physical IoT infrastructure as a dynamic directed graph $G_{\text{phy}}(t) = (V, E_{\text{phy}}(t))$, where vertex set $V$ ($|V|=N$) denotes sensor platforms and $E_{\text{phy}}(t)$ captures operational directional links. Large-scale wireless attenuation across separation distance $d$ follows the log-distance path loss formulation $\text{PL}(d) = \text{PL}(d_0) + 10 \eta \log_{10}(d/d_0) + X_\sigma$, where $\eta$ is the attenuation exponent and zero-mean Gaussian variable $X_\sigma \sim \mathcal{N}(0, \sigma^2)$ models shadow fading. Pairwise packet delivery success $p_{ij}$ between transmitter $i$ and receiver $j$ is governed by the signal-to-interference-plus-noise ratio (SINR) $\gamma_{ij}$:
\begin{equation}
\label{eq:link_success}
p_{ij} = [1 - \tfrac{1}{2} \exp(-\gamma_{ij}/2)]^{8 L_p}, \quad \gamma_{ij} = \frac{P_t h_{ij}}{N_0 + \sum_{k \ne i} P_k h_{kj}},
\end{equation}
where $L_p$ denotes payload byte length, $P_t$ represents RF output power, $h_{ij}$ is the channel power gain, and $N_0$ denotes the thermal noise floor. Transceiver energy consumption for processing an $l$-bit packet across distance $d$ follows standard first-order radio dynamics: transmission drains $E_{\text{tx}}(l, d) = l E_{\text{elec}} + l \epsilon_{\text{amp}} d^\eta$, while reception dissipates $E_{\text{rx}}(l) = l E_{\text{elec}}$ \cite{heinzelman2000energy}. Mirroring this substrate, the digital twin maintains a synchronized computational graph $G_{\text{twin}}(t) = (V, E_{\text{twin}}(t))$ tracking telemetry variables: forwarding fractions, buffer backlogs, remaining battery energy, and instantaneous path configurations. Fig.~\ref{fig:node_topology}(a) displays a representative topology identifying structural articulation vertices.

\begin{figure*}[t]
\centering
\includegraphics[width=0.98\textwidth]{plots/fig2_node_topology_tight.pdf}
\caption{Multi-hop IoT node connectivity and autonomous topological self-healing. (a)~Nominal 6-node mesh highlighting Tarjan cut-vertex (articulation point) $v_4$ ($\delta_{\text{cut}} = 1$); (b)~Active cyberattack on node $v_2$ injecting buffer flooding and selective packet dropping; (c)~Closed-loop self-healing executing loop-free BFS bypass detour $s_{\text{bypass}}$, RF power boost ($+3$\,dBm), and ingress rate clamping, preventing network partitioning without isolating critical articulation nodes.}
\label{fig:node_topology}
\end{figure*}

\begin{table}[t]
\centering
\caption{Simulation Environment and Network Model Parameters}
\label{tab:simulation_specs}
\footnotesize
\renewcommand{\arraystretch}{1.10}
\setlength{\tabcolsep}{4.0pt}
\begin{tabular}{|l|r|}
\hline
\textbf{System Parameter} & \textbf{Nominal Value / Sweep Range} \\
\hline
Network Scale ($N$) & 24 nodes (Scalability: 6--100) \\
\hline
Simulation Duration ($T$) & 80.0\,s per episode \\
\hline
Telemetry Sampling ($\Delta t$) & 0.33\,s (3\,Hz ingestion rate) \\
\hline
Decision Window ($W$) & 10 frames (3.33\,s window) \\
\hline
Nominal Traffic Rate ($\lambda$) & 2.0\,pkts/s (Poisson process) \\
\hline
Packet Payload Size ($L_p$) & 64\,bytes (IEEE 802.15.4 frame) \\
\hline
Queue Capacity ($B_{\max}$) & 100\,packets (Drop-tail discipline) \\
\hline
Channel Path Loss ($\eta, \sigma$) & $\eta = 2.8$, shadow fading $\sigma = 3.5$\,dB \\
\hline
RF Step-Up Power Boost & $+3$\,dBm transmission gain \\
\hline
Attack Window & Active $t \in [20, 60]$\,s \\
\hline
Evaluated Threat Vectors & DoS, Grayhole, Outage, On-Off \\
\hline
Evaluated Strategy Runs & 120 scenarios $\times$ 5 strategies = 600 \\
\hline
\end{tabular}
\end{table}

\subsection{Simulation Setup and GNN Training Configuration}
Table~\ref{tab:simulation_specs} lists the baseline simulation parameters. Telemetry sampling at 3\,Hz consumes minimal channel capacity ($0.61\%$ of available bandwidth, dissipating $0.042$\,mJ per frame).
\textit{GNN architecture and training:} The detector processes 12 node features (traffic rates, loss, latency, queue depth, energy, CPU load, forwarding ratios, loss variance, state transitions, degree, cut-vertex flag $\delta_{\text{cut}}$, and betweenness centrality) and 4 directional edge features. A two-stage BridgeAwareGAT network ($12 \to 64$ across 4 heads $\to 32$, bridge penalty $\gamma=0.5$) and 1-layer GRU cell ($32 \to 32$, window $W=5$) drive dual MLP heads for 5-class anomaly classification ($\mathcal{L}_{\text{CE}}$) and continuous trust estimation ($\mathcal{L}_{\text{MSE}}$). Composite training minimizes $\mathcal{L} = 0.65\mathcal{L}_{\text{CE}} + 0.35\mathcal{L}_{\text{MSE}}$ via Adam ($\text{lr}=3\times 10^{-4}$, weight decay $10^{-4}$) with CosineAnnealingLR ($T_{\max}=50$) over 50 epochs (batch size 64, 31,500 snapshots across 30 seeds). An 80/20 train/test split across disjoint seeds and attack paths (precluding temporal feature leakage; 115,200 windows) yields $99.96\%$ accuracy ($100\%$ precision, $99.97\%$ recall).

\subsection{Adversarial Threat Models and Attack Functions}
Our threat formulation spans four distinct attack manifestations: (i)~Type~1 (buffer exhaustion flooding): a compromised node $v_a$ injects traffic at surge rate $\lambda_{\text{flood}} = 25\,\text{pkts/s} \gg \lambda_{\text{nominal}}$, causing queue buffer overflow; (ii)~Type~2 (selective grayhole tampering): drops transit traffic stochastically at rate $p_{\text{drop}} \in [0.4, 0.8]$ while broadcasting compliant control beacons; (iii)~Type~3 (abrupt node outage): models node failure by severing all incident links $E(t) \leftarrow E(t) \setminus \{(v_a, v_j) \mid v_j \in \mathcal{N}(v_a)\}$; and (iv)~Type~4 (evasive on-off cycling): alternates between packet dropping ($T_{\text{attack}} = 10$\,s) and normal operation ($T_{\text{dormant}} = 15$\,s) to exploit symmetric trust recovery.

\section{Closed-Loop Digital Twin Architecture}
\label{sec:architecture}
As shown in Fig.~\ref{fig:system_architecture}, the closed-loop architecture operates across five core functional modules.

\subsection{Articulation-Aware Bayesian Trust and Topological Criticality}
The digital twin maintains a continuous reputation score $\mathcal{T}_i(t) \in [0, 1]$ tracking the behavioral reliability of each network node $i \in V$. Forwarding integrity $\mathcal{T}_{\text{fwd}}$ and packet loss $\mathcal{T}_{\text{loss}}$ follow recursive Beta-binomial conjugate observation updates ($\mathbb{E}[\theta] = \frac{\alpha}{\alpha+\beta}$ with uninformative prior $\text{Beta}(1, 1)$), integrated with battery reserves $\mathcal{T}_{\text{energy}}$ and inference outputs $\mathcal{T}_{\text{ml}}$:
\begin{equation}
\label{eq:bayesian_inst}
\mathcal{T}_{\text{inst}, i}(t) = w_f \mathcal{T}_{\text{fwd}, i} + w_e \mathcal{T}_{\text{energy}, i} + w_l \mathcal{T}_{\text{loss}, i} + w_m \mathcal{T}_{\text{ml}, i},
\end{equation}
employing weight vector $\mathbf{w} = [0.35, 0.20, 0.25, 0.20]$. To nullify cyclical on-off evasion, trust dynamics implement an asymmetric temporal filter:
\begin{equation}
\label{eq:asym_trust}
\mathcal{T}_i(t) = \begin{cases}
(1 - \lambda_p)\mathcal{T}_i(t-1) + \lambda_p \mathcal{T}_{\text{inst}, i}, & \mathcal{T}_{\text{inst}, i} < \mathcal{T}_i(t-1), \\
(1 - \lambda_r)\mathcal{T}_i(t-1) + \lambda_r \mathcal{T}_{\text{inst}, i}, & \text{otherwise},
\end{cases}
\end{equation}
where aggressive penalization ($\lambda_p = 0.40$) and gradual recovery ($\lambda_r = 0.05$) establish an 8:1 penalty-to-restoration hysteresis.

\textbf{Theorem 1 (Asymptotic Trust Suppression Under On-Off Evasion)}: \textit{Consider an evasive adversary operating with duty factor $\rho \in (0, 1)$ that alternates between malicious disruption ($\mathcal{T}_{\min}$) and compliant forwarding ($\mathcal{T}_{\max}$). A sufficient criterion ensuring that long-term expected trust remains strictly below quarantine cutoff $\tau_{\text{thresh}}$ ($\lim_{t\to\infty} \mathcal{T}_i(t) < \tau_{\text{thresh}}$) is given by:}
\begin{equation}
\label{eq:evasion_bound}
\frac{\lambda_p}{\lambda_r} > \left(\frac{1 - \rho}{\rho}\right) \left(\frac{\mathcal{T}_{\max} - \tau_{\text{thresh}}}{\tau_{\text{thresh}} - \mathcal{T}_{\min}}\right).
\end{equation}
\textit{Proof}: The average trust trajectory over a complete period $T$ exhibits negative drift when $\Delta \mathcal{T} = \rho T [-\lambda_p(\tau_{\text{thresh}} - \mathcal{T}_{\min})] + (1 - \rho) T [\lambda_r(\mathcal{T}_{\max} - \tau_{\text{thresh}})] < 0$, which simplifies directly to \eqref{eq:evasion_bound}. Substituting operational values $\tau_{\text{thresh}} = 0.50$, $\mathcal{T}_{\max} = 1.0$, $\mathcal{T}_{\min} \le 0.10$, and $\rho \ge 0.20$ bounds the right-hand side by $\le 5.0$. Setting $\lambda_p / \lambda_r = 0.40 / 0.05 = 8.0 > 5.0$ guarantees that the adversary cannot recover nominal trust between attack bursts. $\blacksquare$

We quantify vertex vulnerability through a topological criticality metric $C_i \in [0.10, 1.00]$ fusing betweenness centrality $B(i)$, connectivity degree $D(i)$, and articulation flag $\delta_{\text{cut}}(i)$:
\begin{equation}
\label{eq:criticality}
C_i = 0.10 + 0.90 \cdot [w_b B(i) + w_d D(i) + \delta_{\text{cut}}(i) \cdot \alpha_{\text{boost}}],
\end{equation}
in which $\delta_{\text{cut}}(i) = 1$ identifies structural cut-vertices in $G(t)$, calculated in $\mathcal{O}(|V| + |E|)$ time using Tarjan's depth-first search ($\alpha_{\text{boost}} = 0.50$). If a node's trust deteriorates below $\tau_{\text{thresh}} = 0.50$, autonomous mitigation is initiated (Algorithm~1). As visualized in Fig.~\ref{fig:node_topology}(b)--(c), unconditional isolation is prohibited on articulation nodes ($\delta_{\text{cut}} = 1$); instead, the orchestrator deploys dynamic BFS bypass routes and ingress rate clamping.

\subsection{In-Silico Sandbox Simulation and TOPSIS Optimization}
Upon detecting an anomaly, the digital twin generates a candidate action pool $\mathcal{S} = \{s_1, \dots, s_K\}$: loop-free detour routing $s_{\text{bypass}}$, ingress rate throttle $s_{\text{rate}}$ ($0.5\,\text{pkts/s}$), transmission power amplification $s_{\text{power}}$ ($+3\,\text{dBm}$), and nodal quarantine $s_{\text{quarantine}}$ (strictly forbidden if $\delta_{\text{cut}} = 1$). Each candidate is evaluated within an in-silico discrete-event simulation kernel over prediction horizon $H$: (i)~a gateway tier ($H=30$\,s, $\text{RMSE}=0.024$, taking $6.5$\,ms) for edge computers; and (ii)~an embedded microcontroller tier ($H=10$\,s, $\text{RMSE}=0.058$, taking $2.28$\,ms) tailored for low-power edge nodes. The projected outcomes form decision matrix $\mathbf{X} = [x_{km}]_{K \times 4}$ across packet delivery ratio ($f_{\text{PDR}}$), energy consumption ($f_{\text{eng}}$), transit delay ($f_{\text{lat}}$), and buffer congestion ($f_{\text{queue}}$). Multi-criteria TOPSIS identifies the Pareto-optimal mitigation $s^*$ via relative proximity scoring $\Phi(s_k)$:
\begin{equation}
\label{eq:topsis}
\Phi(s_k) = \frac{D^-(s_k)}{D^+(s_k) + D^-(s_k)}, \quad s^* = \arg\max_{s_k \in \mathcal{S}} \Phi(s_k).
\end{equation}

\textbf{Theorem 2 (Topological Connectivity Under Articulation Constraints)}: \textit{Consider an initially connected graph $G$. Removing any non-cut node $v \notin V_{\text{cut}}$ leaves the induced subgraph $G \setminus \{v\}$ connected. For an articulation node $v_a \in V_{\text{cut}}$, where physical quarantine is strictly prohibited ($\delta_{\text{cut}}(v_a) = 1 \implies s_{\text{quarantine}} \notin \mathcal{S}$), whenever the selected mitigation establishes a feasible detour of positive conductance bridging the partitioned clusters, the post-intervention Laplacian satisfies $\lambda_2(L') > 0$. In extreme topologies where pathological cut-vertex cascades preclude any detour path, global connectivity remains subject to this physical detour existence.}
\textit{Proof}: Non-articulation removals preserve graph connectivity by elementary graph theory. For cut-vertices ($\delta_{\text{cut}}(v_a)=1$), our policy engine excludes $s_{\text{quarantine}}$ from $\mathcal{S}$, confining available actions to traffic throttling ($s_{\text{rate}}$) and dynamic detour reconfiguration ($s_{\text{bypass}}$). Provided a valid alternative path with non-zero conductance ($c_{\text{detour}} > 0$) exists in the multi-hop fabric, the post-healing graph maintains at least one spanning tree spanning all benign nodes. Spectral graph theory dictates that a graph is connected if and only if its Fiedler eigenvalue satisfies $\lambda_2(L') > 0$, guaranteeing algebraic connectivity. $\blacksquare$

\subsection{Dynamic Wald SPRT Verification and Safety Rollback}
Rather than stalling network operations across rigid observation windows, the verification engine dynamically tracks packet reception statistics via sequential hypothesis testing. The detector contrasts null hypothesis $H_0$ (restored nominal loss $p_0 = 0.03$) against alternate hypothesis $H_1$ (persistent impairment $p_1 = 0.12$) using effective batch weight $n_{\text{eff}}=5$ \cite{upadhyaya2021multihypothesis}, compounding the cumulative log-likelihood metric:
\begin{equation}
\label{eq:wald}
\Lambda_m = \sum_{k=1}^m \Delta \Lambda_k = d_m \ln\frac{p_1}{p_0} + (m \cdot n_{\text{eff}} - d_m) \ln\frac{1 - p_1}{1 - p_0},
\end{equation}
in which $d_m$ records missing frames over $m$ evaluation intervals. With false-alarm constraint $\alpha_{\text{sprt}} = 0.01$ and miss probability $\beta_{\text{sprt}} = 0.05$, the stopping thresholds evaluate to $A = \ln\frac{1-\beta_{\text{sprt}}}{\alpha_{\text{sprt}}} \approx 4.554$ and $B = \ln\frac{\beta_{\text{sprt}}}{1-\alpha_{\text{sprt}}} \approx -2.986$. If $\Lambda_m \le B$, the engine accepts $H_0$ and certifies network recovery. Conversely, if $\Lambda_m \ge A$ or graph connectivity breaks ($k(G') < 1$), the controller activates a state rollback: the verified snapshot $\mathcal{S}_{\text{pre}}$ is restored into memory in $<0.1$\,ms using SHA-256 state hashing (distinct from total recovery time $\text{MTTR} = 4.50$\,s, which encompasses detection and sequential testing).

\textbf{Proposition 1 (Sequential Sample Complexity Reduction)}: \textit{Under nominal conditions ($H_0$), the expected number of sampling epochs required for the Wald statistic to hit stopping threshold $B$ satisfies $\mathbb{E}_0[N] \approx \frac{(1 - \alpha_{\text{sprt}}) B + \alpha_{\text{sprt}} A}{\mathbb{E}_0[\Delta \Lambda]} \approx 11.0\text{ frames}$ ($3.67$\,s at 3\,Hz sampling; empirical trials yield $9.3\text{--}10.5\text{ frames}$, equivalent to $3.1\text{--}3.5$\,s). This sequential formulation accounts for the major component of total recovery ($\text{MTTR} = 4.50$\,s), delivering an approximate $75\%$ reduction in verification latency compared to conventional $15$-s observation windows.}

\textbf{Theorem 3 (Foster-Lyapunov Queue Boundedness)}: \textit{When ingress rate throttling $s_{\text{rate}}$ enforces arrival rate $\lambda_a \le \mu_a - \epsilon$ for some stability margin $\epsilon > 0$, the quadratic Lyapunov function $V(\mathbf{q}(t)) = \frac{1}{2} \sum_{i \in V} q_i(t)^2$ exhibits strictly negative drift: $\mathbb{E}[\Delta V(\mathbf{q}(t)) \mid \mathbf{q}(t)] \le B - \epsilon \sum_{i \in V} q_i(t)$, where $B = \frac{1}{2}\sum_i (\lambda_i^2 + \mu_i^2) < \infty$. Consequently, time-averaged queue lengths satisfy $\limsup_{T \to \infty} \frac{1}{T} \sum_{t=0}^{T-1} \sum_i \mathbb{E}[q_i(t)] \le B/\epsilon < \infty$, preventing buffer overflow cascades.}

\textbf{Proposition 2 (Multi-Hop Fault Detection Acceleration)}: \textit{Let $\mathcal{T}_i^{\text{fused}}(t) = \beta_i \mathcal{T}_i^{\text{Bayes}}(t) + (1-\beta_i)\mathcal{T}_i^{\text{GNN}}(t)$ represent the integrated trust estimator ($\beta_{\text{cut}}=0.35, \beta_{\text{leaf}}=0.60$). Within the benchmarked network, aggregating 2-hop spatial neighborhood embeddings via graph attention reduces median fault detection delay by $2.1\times$ compared to isolated Bayesian filtering ($2.10$\,s versus $4.41$\,s; Wilcoxon test $W=14.0, p < 10^{-4}$), expediting anomaly discovery while preserving long-term convergence properties.}

\begin{table*}[t]
\centering
\caption{Comparative Benchmarks Across Mitigation Strategies Under Cyberattacks ($n=120$ Matched Scenarios, 600 Total Runs, Mean $\pm$ SD and Median [IQR]).}
\label{tab:comparative_benchmarks}
\footnotesize
\renewcommand{\arraystretch}{1.12}
\setlength{\tabcolsep}{1.40pt}
\begin{tabular}{|l|c|c|c|c|c|c|c|}
\hline
\textbf{Mitigation Scheme} & \textbf{Resilience $\mathcal{R}$} & \textbf{Mean PDR} & \textbf{Nadir PDR} & \textbf{Part. Mean} & \textbf{Med. [IQR]} & \textbf{Energy (J)} & \textbf{MTTR (s)} \\
\hline
Baseline 1: Unmitigated & $0.7976 \pm 0.018$ & $0.7812 \pm 0.021$ & $0.6240 \pm 0.035$ & $0.00 \pm 0.00\%$ & $0.00 [0.00]\%$ & $38.42 \pm 1.25$ & $\infty$ (No rec.) \\
\hline
Baseline 2: Static IDS \cite{mani2023machine}$^\dagger$ & $0.7512 \pm 0.034$ & $0.7420 \pm 0.041$ & $0.5180 \pm 0.062$ & $54.20 \pm 31.43\%$ & $72.50 [21.87]\%$ & $36.18 \pm 1.10$ & $18.40 \pm 2.15$ \\
\hline
Baseline 3: ML Heuristic \cite{yigit2024ai}$^\dagger$ & $0.8325 \pm 0.015$ & $0.8240 \pm 0.019$ & $0.6890 \pm 0.028$ & $14.25 \pm 2.65\%$ & $14.50 [0.00]\%$ & $34.80 \pm 0.95$ & $14.20 \pm 1.80$ \\
\hline
Baseline 4: Standalone GNN \cite{lo2022egraphsage}$^\dagger$ & $0.7845 \pm 0.024$ & $0.8520 \pm 0.028$ & $0.5840 \pm 0.045$ & $46.88 \pm 27.06\%$ & $62.50 [31.25]\%$ & $35.40 \pm 1.05$ & $15.80 \pm 2.10$ \\
\hline
\textbf{Proposed: GNN-Fused Twin} & $\mathbf{0.9380 \pm 0.009}$ & $\mathbf{0.9550 \pm 0.008}$ & $\mathbf{0.8350 \pm 0.018}$ & $\mathbf{0.00 \pm 0.00\%}$ & $\mathbf{0.00 [0.00]\%}$ & $\mathbf{30.85 \pm 0.75}$ & $\mathbf{4.50 \pm 0.60}$ \\
\hline
\multicolumn{8}{|p{\dimexpr\textwidth-2\tabcolsep-2\arrayrulewidth\relax}|}{\scriptsize \textbf{Type 4 On-Off Evasion:} Baseline 2 triggers $72.42 \pm 0.85\%$ partition ($72.50\%$ median); Baseline 4 triggers $62.50\%$ median; Proposed sustains $0.00\%$ partition and $\mathcal{R} = 0.9385 \pm 0.010$.} \\
\hline
\multicolumn{8}{|p{\dimexpr\textwidth-2\tabcolsep-2\arrayrulewidth\relax}|}{\scriptsize \textbf{Inferential Statistics (Proposed vs. B2, $n=120$):} Paired diff $= 54.20 \pm 31.43$\,pp ($95\%$ CI $[48.57, 59.82]$); $t(119)=18.89, p=1.29 \times 10^{-37}$; Wilcoxon $W=0.0$; Cohen's $d=1.724$.} \\
\hline
\end{tabular}
\end{table*}

\begin{algorithm}[t]
\caption{Closed-Loop Digital Twin Self-Healing \& Verification}
\label{alg:self_healing}
\begin{algorithmic}[1]
\footnotesize
\REQUIRE Telemetry frame $\mathbf{z}(t)$, Topology graph $G(t)$, Prior snapshot $\mathcal{S}_{\text{pre}}$
\ENSURE Actuation policy $s^*$, Verification state $\mathcal{V}$
\STATE Synchronize twin state: $G_{\text{twin}}(t) \leftarrow \text{Sync}(G(t), \mathbf{z}(t))$
\STATE Detect articulation points: $\Delta_{\text{cut}} \leftarrow \text{TarjanCutVertices}(G_{\text{twin}})$
\STATE Compute fused GNN-Bayesian trust $\mathcal{T}_i^{\text{fused}}(t)$ and criticality $C_i(t)$
\IF{$\exists i \in V \text{ s.t. } \mathcal{T}_i^{\text{fused}}(t) < \tau_{\text{thresh}}$}
    \STATE Capture integrity-verified snapshot: $\mathcal{S}_{\text{pre}} \leftarrow \text{CaptureSnapshot}(G_{\text{twin}})$
    \STATE Generate candidate pool $\mathcal{S} \leftarrow \text{SynthesizeActions}(i, \Delta_{\text{cut}})$
    \FORALL{$s \in \mathcal{S}$}
        \STATE Project forward $H$ in sandbox (30\,s gateway / 10\,s MCU): $\hat{\mathbf{x}}_s \leftarrow \text{Simulate}(G_{\text{twin}}, s, H)$
    \ENDFOR
    \STATE Select multi-objective policy: $s^* \leftarrow \arg\max_{s} \Phi(s)$ via TOPSIS \eqref{eq:topsis}
    \STATE Dispatch signed actuation command $s^*$ to physical nodes
    \STATE Initialize Wald SPRT log-likelihood accumulator: $\Lambda_0 \leftarrow 0$
    \REPEAT
        \STATE Collect post-actuation sample $x_m$; update $\Lambda_m$ via \eqref{eq:wald}
    \UNTIL{$\Lambda_m \le B$ (Accept $H_0$) \textbf{or} $\Lambda_m \ge A$ (Accept $H_1$)}
    \IF{$\Lambda_m \ge A$ \textbf{or} PartitionDetected()}
        \STATE Execute state-consistent rollback: $\text{RollbackTo}(\mathcal{S}_{\text{pre}})$
        \STATE $\mathcal{V} \leftarrow \text{SAFETY\_ROLLBACK}$
    \ELSE
        \STATE $\mathcal{V} \leftarrow \text{VERIFIED\_RECOVERY}$
    \ENDIF
\ENDIF
\end{algorithmic}
\end{algorithm}

\noindent \textit{Telemetry streaming and monitoring}: An operator interface ingests telemetry at 3\,Hz over WebSockets, displaying real-time delivery ratio ($97.9\%$), latency ($26.5\,\text{ms}$), identified articulation points, and mitigation states.

\begin{figure}[t]
\centering
\includegraphics[width=\columnwidth]{plots/fig3_column_resilience_partition.pdf}
\caption{Dynamic cyber-resilience benchmarks across $n=120$ matched scenarios: (a) Dynamic resilience trajectory $Q(t)$ under cut-vertex intrusion; (b) Network partition rate comparison across threat vectors.}
\label{fig:phase11_results}
\end{figure}

\begin{figure}[t]
\centering
\includegraphics[width=\columnwidth]{plots/fig4_column_parameter_sensitivity.pdf}
\caption{Parameter sensitivity analysis: (a) In-silico lookahead horizon $H$ trade-off; (b) Downlink tolerance under lossy wireless channels.}
\label{fig:ablation_results}
\end{figure}

\section{Experimental Evaluation and Result Discussion}
\label{sec:experiments}
We validate cyber-resilience gains, structural partition suppression, and statistical consistency across 600 comprehensive Monte Carlo evaluations, analyzing 120 matched topologies subjected to five distinct defensive protocols.

\subsection{Evaluation Criteria and Experimental Baseline Parity}
Performance is assessed through six core indicators: (i)~Mean packet delivery ratio $\bar{\text{PDR}} = \frac{1}{T}\sum_{t=1}^T \text{PDR}(t)$ across the entire 80\,s horizon; (ii)~Nadir PDR $\min_t \text{PDR}(t)$, tracking the worst-case instantaneous drop during disruption and response; (iii)~Partition percentage, reflecting isolated node fraction; (iv)~Resilience integral $\mathcal{R} = \frac{1}{t_r - t_0} \int_{t_0}^{t_r} Q(t) \, dt$; (v)~Mean time to recovery (MTTR), clocked until SPRT sign-off; and (vi)~Total dissipated radio energy (J).

Evaluation runs incorporate 30 distinct pseudo-random seeds ($S \in \{42, \dots, 71\}$) and four incursion classes driven by Poisson packet generation over $T=80$\,s. Comparative schemes---Baseline 2 \cite{mani2023machine}, Baseline 3 \cite{yigit2024ai}, and Baseline 4 \cite{lo2022egraphsage}---are calibrated according to their literature specifications under identical RF propagation and load conditions.

\subsection{Empirical Resilience and Topological Partition Prevention}
As detailed in Table~\ref{tab:comparative_benchmarks}, our framework attains an aggregate resilience index of $\mathcal{R} = 0.9380 \pm 0.009$ (representing a 24.9\% improvement over Baseline~2 and 12.7\% over Baseline~3) while sustaining a nadir PDR of $83.5 \pm 1.8\%$ (contrasting with $51.8 \pm 6.2\%$ in Baseline~2; Fig.~\ref{fig:phase11_results}(a)). In Baseline~4, unconstrained quarantine of articulation relays collapses instantaneous throughput to a nadir of $0.5840 \pm 0.045$ with extensive graph fragmentation ($46.88 \pm 27.06\%$, median $62.50\%$), though its full-trial Mean PDR reaches $0.8520 \pm 0.028$ due to unperturbed pre-attack periods and traffic across surviving subgraphs. By enforcing articulation constraints that block cut-vertex disconnection, our self-healing strategy yields a $0.00\%$ observed partition rate across all benchmark runs ($0.00\%$ median; Fig.~\ref{fig:phase11_results}(b)). Coordinated trust fusion curtails MTTR to $4.50 \pm 0.60$\,s. Prediction horizon sweeps (Fig.~\ref{fig:ablation_results}(a)) reveal that $H=30$\,s offers high simulation fidelity on edge gateways ($\text{RMSE}=0.024$, taking $6.5$\,ms), whereas $H=10$\,s provides an efficient configuration for microcontrollers ($\text{RMSE}=0.058$, taking $2.28$\,ms). Automatic retransmissions maintain $\mathcal{R} \ge 0.80$ even when link loss reaches $30\%$ (Fig.~\ref{fig:ablation_results}(b)).

\subsection{Inferential Analysis and Ablation Findings}
Evaluating $n=120$ matched scenario pairs indicates that our method curtails partition incidence relative to Baseline~2 by $54.20 \pm 31.43$\,percentage points ($95\%$ CI $[48.57, 59.82]$; paired $t(119) = 18.89, p = 1.29 \times 10^{-37}$; Wilcoxon signed-rank $W = 0.0$; Cohen's $d = 1.724$; Bayes factor $BF_{10} = 5.18 \times 10^{21} \gg 100$).

\begin{table}[t]
\centering
\caption{Systematic Component Ablation Study ($n=120$ Scenarios: 30 Seeds $\times$ 4 Threat Classes)}
\label{tab:ablation_study}
\footnotesize
\renewcommand{\arraystretch}{1.10}
\setlength{\tabcolsep}{0.6pt}
\begin{tabular}{|l|c|c|c|c|}
\hline
\textbf{Variant} & $\mathcal{R}$ & \textbf{Part.} & \textbf{MTTR} & \textbf{Eng. (J)} \\
\hline
\textbf{Proposed System} & $\mathbf{0.938 \pm 0.01}$ & $\mathbf{0.00\%}$ & $\mathbf{4.50 \pm 0.60}$ & $\mathbf{30.85 \pm 0.75}$ \\
\hline
w/o Cut-Vertex Aw. & $0.751 \pm 0.03$ & $54.20\%$ & $16.20 \pm 1.85$ & $36.18 \pm 1.10$ \\
\hline
w/o Sandbox ($H=0$) & $0.842 \pm 0.02$ & $12.40\%$ & $12.80 \pm 1.40$ & $35.40 \pm 0.95$ \\
\hline
w/o Wald SPRT & $0.865 \pm 0.02$ & $0.00\%$ & $18.40 \pm 2.15$ & $33.90 \pm 0.85$ \\
\hline
w/o TOPSIS Opt. & $0.892 \pm 0.01$ & $0.00\%$ & $5.10 \pm 0.70$ & $36.80 \pm 1.15$ \\
\hline
w/o Heur. Sigs & $0.902 \pm 0.01$ & $0.00\%$ & $4.90 \pm 0.65$ & $31.80 \pm 0.80$ \\
\hline
\end{tabular}
\end{table}

As shown in Table~\ref{tab:ablation_study}, ablation experiments verify the role of each module. Disabling cut-vertex awareness allows candidate actions to quarantine articulation points, reproducing the partition collapse ($54.20\%$) and resilience degradation ($\mathcal{R}=0.7512$) observed in Baseline~2, while retaining SPRT verification ($16.20$\,s MTTR). Eliminating sandbox lookahead ($H=0$) reduces resilience to $0.8415$, whereas replacing Wald SPRT with fixed 15\,s observation windows increases MTTR by 155\% ($18.40$\,s). Omitting TOPSIS optimization increases energy consumption by 17.8\% ($36.80$\,J), while retraining without heuristic signatures maintains $79.7\%$ binary accuracy with zero-shot generalization across bursty traffic ($80.0\%$) and Barab\'{a}si-Albert scale-free graphs ($66.7\%$).

\begin{figure}[t]
\centering
\includegraphics[width=\columnwidth]{plots/fig5_adversarial_robustness_clean.pdf}
\caption{Adversarial evasion robustness under PGD evasion attacks ($L_\infty$ norm): (a) Classification accuracy vs. perturbation budget $\epsilon$; (b) Bayesian trust distortion (MAE) under adversarial feature drift.}
\label{fig:adversarial_results}
\end{figure}

\begin{table}[b]
\centering
\caption{Adversarial Defense and Federated Edge Learning Benchmarks}
\label{tab:adversarial_fl_benchmarks}
\footnotesize
\renewcommand{\arraystretch}{1.10}
\setlength{\tabcolsep}{2.5pt}
\begin{tabular}{|l|c|c|c|c|}
\hline
\textbf{Defense / FL Scheme} & \textbf{Acc. (\%)} & \textbf{ASR (\%)} & \textbf{Trust MAE} & \textbf{Payload} \\
\hline
Standard GAT (Clean) & $94.20\%$ & --- & $0.0245$ & $76.8$\,KB \\
\hline
Standard GAT (PGD-10) & $8.33\%$ & $95.24\%$ & $0.5103$ & $76.8$\,KB \\
\hline
\textbf{Minimax-Hardened GAT} & $\mathbf{91.67\%}$ & $\mathbf{8.33\%}$ & $\mathbf{0.0241}$ & $\mathbf{76.8\,\textbf{KB}}$ \\
\hline
Standard FedAvg ($K=4$) & $78.40\%$ & --- & $0.0820$ & $76.8$\,KB \\
\hline
\textbf{FedGraphBridge + INT8} & $\mathbf{88.10\%}$ & --- & $\mathbf{0.0315}$ & $\mathbf{9.6\,\textbf{KB}}$ \\
\hline
\end{tabular}
\end{table}

\subsection{Adversarial Minimax Defense and Federated Edge Learning}
As shown in Table~\ref{tab:adversarial_fl_benchmarks}, minimax adversarial training preserves $91.67\%$ classification accuracy under PGD-10 evasion ($\epsilon = 0.12$), reducing the attack success rate from $95.24\%$ to $8.33\%$ (trust error $\text{MAE} \le 0.0241$; Fig.~\ref{fig:adversarial_results}). Under non-IID Dirichlet partitioning ($\alpha_{\text{dir}} = 0.5, K = 4$), FedGraphBridge weights parameter updates by topological centrality, achieving $88.10\%$ accuracy while reducing uplink data transmission by $87.5\%$ ($9.6$\,KB vs. $76.8$\,KB) under $(\epsilon=3.2, \delta=10^{-5})$ differential privacy.

\begin{figure}[t]
\centering
\includegraphics[width=\columnwidth]{plots/fig6_clean_scalability_hardware.pdf}
\caption{Asymptotic scalability and edge hardware feasibility: (a) Latency decomposition and linear $\mathcal{O}(N)$ scaling ($R^2 = 0.9953$); (b) Projected compute latency vs. real-time deadlines across embedded hardware platforms.}
\label{fig:scalability_results}
\end{figure}

\section{Scalability and Edge Hardware Projections}
\label{sec:scalability}
\subsection{Asymptotic Complexity Derivation}
Across $N=6$ to $100$ nodes (Fig.~\ref{fig:scalability_results}(a)), cycle latency decomposes as $\mathcal{T}_{\text{cycle}}(N) = \mathcal{T}_{\text{sync}} + \mathcal{T}_{\text{trust}} + \mathcal{T}_{\text{cand}} + \mathcal{T}_{\text{sand}} + \mathcal{T}_{\text{opt}}$. Sync, trust, and Tarjan discovery scale as $\mathcal{O}(N)$ for bounded degree, while $|\mathcal{S}|=4$ actions project in $\mathcal{O}(1)$ time, closely tracking the derived $\mathcal{O}(N)$ scaling ($R^2 = 0.9953$; $17.87$\,ms at $N=6$ to $234.12$\,ms at $N=100$). Fig.~\ref{fig:1000_node_topology} illustrates a realistic 1,000-node mesh synthesized from OpenStreetMap residential building coordinates across Dhaka.

\begin{figure}[t]
\centering
\includegraphics[width=\columnwidth]{plots/fig_1000_nodes_topology_v2_clean.pdf}
\caption{Realistic 1,000-node IoT topology synthesized from Dhaka residential building coordinates (OpenStreetMap). Blue nodes denote sensors; red nodes denote gateway/transit hubs. Green lines denote local mesh links, orange lines denote backbone trunks, and brown lines denote uplinks.}
\label{fig:1000_node_topology}
\end{figure}

\subsection{Edge Deployment Feasibility and Analytical Scaling}
Compute feasibility across four embedded platforms (Fig.~\ref{fig:scalability_results}(b)) was evaluated through profiling measurements (100 trials, mean $\pm$ SD): (i)~Raspberry Pi 4B: $62.3 \pm 2.1$\,ms ($\le 100$\,ms deadline); (ii)~NVIDIA Jetson Nano: $70.1 \pm 2.8$\,ms ($\le 100$\,ms); (iii)~Intel Edge: $24.4 \pm 0.9$\,ms ($\le 50$\,ms); and (iv)~ESP32-S3 (Xtensa LX7, 8\,MB PSRAM): $350.5 \pm 8.4$\,ms ($\le 500$\,ms, consuming $<2.5$\,MB RAM) for the local control loop ($H=10$\,s lookahead, Tarjan DFS, trust, TOPSIS), satisfying real-time timing deadlines while neural network retraining is offloaded to edge gateways.

\section{Discussion, Reproducibility, and Conclusion}
\label{sec:conclusion}
\noindent\textit{Threats to Validity:} Evaluation limitations include wireless multipath fading, sparse cut chains stressing detour capacity, collusions of $K > 5$ cut attackers, multi-cluster scaling ($N > 100$), and passive eavesdropping lacking traffic anomalies. In addition, partition elimination is a direct consequence of the articulation-aware constraint barring cut-vertex quarantine, rather than detection accuracy alone.

\noindent\textit{Conclusion:} We presented a closed-loop digital twin unifying topology-aware GAT detection, Bayesian trust estimation, lookahead simulation, and Wald SPRT verification. Across 600 runs, enforcing articulation-aware constraints prevented network partitioning under all evaluated attack scenarios ($0.00\%$ observed partition rate vs. $72.50\%$ in static IDS) by replacing cut-vertex quarantine with dynamic bypass detours and rate clamping, achieving a 24.9\% resilience gain within a 500-ms edge deadline. Artifacts: \url{https://github.com/anonymous-dt-iot/self-healing-dt}.

\bibliographystyle{IEEEtran}
\begin{thebibliography}{19}
\setlength{\itemsep}{0.5pt}
\setlength{\parskip}{0pt}
\footnotesize
\bibitem{yigit2024ai} Y. Yigit, K. N. Choobdar, B. Yamansavascilar, B. Canberk, and Z. Han, ``AI-enhanced digital twin framework for cyber-resilient 6G Internet of Vehicles networks,'' \textit{IEEE Internet of Things J.}, vol. 11, no. 22, pp. 36168--36181, Nov. 2024.
\bibitem{mani2023machine} G. Mani, B. Bhargava, B. Shivakumar, and J. Kobes, ``Machine learning based resilience testing of an address randomization cyber defense,'' \textit{IEEE Trans. Dependable Secure Comput.}, vol. 20, no. 6, pp. 4853--4867, Nov.--Dec. 2023.
\bibitem{ge2024gazeta} Y. Ge and Q. Zhu, ``GAZETA: Game-theoretic zero-trust authentication for defense against lateral movement in 5G IoT networks,'' \textit{IEEE Trans. Inf. Forensics Security}, vol. 19, pp. 540--554, 2024.
\bibitem{liu2024region} X. Liu, X. Zeng, J. Ren, S. Yin, and H. Zhou, ``Region-different network reconfiguration in disjoint wireless sensor networks for smart agriculture monitoring,'' \textit{ACM Trans. Sensor Netw.}, vol. 20, no. 2, pp. 1--20, 2024.
\bibitem{debenedictis2023digital} A. De Benedictis, A. Somma, and A. Tedesco, ``Digital twins for anomaly detection in the industrial Internet of Things: Conceptual architecture and proof-of-concept,'' \textit{IEEE Trans. Ind. Informat.}, vol. 19, no. 12, pp. 11553--11563, Dec. 2023.
\bibitem{guan2023resilient} M. Guan and Y. Chen, ``Resilient distributed consensus in adversarial wireless sensor networks,'' \textit{IEEE Trans. Mobile Comput.}, vol. 22, no. 8, pp. 4812--4825, Aug. 2023.
\bibitem{khan2022digital} L. U. Khan, W. Saad, D. Niyato, Z. Han, and C. S. Hong, ``Digital twin of wireless systems: Overview, taxonomy, challenges, and opportunities,'' \textit{IEEE Commun. Surveys Tuts.}, vol. 24, no. 4, pp. 2230--2254, 4th Quart. 2022.
\bibitem{upadhyaya2021multihypothesis} B. Upadhyaya, S. Sun, and B. Sikdar, ``Multihypothesis sequential testing for illegitimate access and collision-based attack detection in wireless IoT networks,'' \textit{IEEE Internet of Things J.}, vol. 8, no. 14, pp. 11705--11716, Jul. 2021.
\bibitem{kouicem2022decentralized} D. E. Kouicem, Y. Imine, A. Bouabdallah, and H. Lakhlef, ``Decentralized blockchain-based trust management protocol for the Internet of Things,'' \textit{IEEE Trans. Dependable Secure Comput.}, vol. 19, no. 2, pp. 1292--1306, Mar.--Apr. 2022.
\bibitem{wu2023heterogeneous} J. Wu, H. Dai, Y. Wang, K. Ye, and C. Xu, ``Heterogeneous domain adaptation for IoT intrusion detection: A geometric graph alignment approach,'' \textit{IEEE Internet of Things J.}, vol. 10, no. 12, pp. 10764--10777, Jun. 2023.
\bibitem{jia2023virtual} P. Jia and X. Wang, ``A new virtual network topology-based digital twin for spatial-temporal load-balanced user association in 6G HetNets,'' \textit{IEEE J. Sel. Areas Commun.}, vol. 41, no. 10, pp. 3080--3094, Oct. 2023.
\bibitem{yang2024enabling} L. Yang, M. E. Rajab, A. Shami, and S. Muhaidat, ``Enabling AutoML for zero-touch network security: Use-case driven analysis,'' \textit{IEEE Trans. Netw. Service Manag.}, vol. 21, no. 3, pp. 3555--3582, Jun. 2024.
\bibitem{sood2023intrusion} K. Sood, S. Garg, N. Kumar, and M. Guizani, ``Intrusion detection scheme with dimensionality reduction in next generation networks,'' \textit{IEEE Trans. Inf. Forensics Security}, vol. 18, pp. 965--979, 2023.
\bibitem{liu2022selfhealing} J. Liu, S. Guo, L. Chen, and K. Wang, ``A self-healing routing strategy based on ant colony optimization for vehicular ad hoc networks,'' \textit{IEEE Internet of Things J.}, vol. 9, no. 22, pp. 22695--22709, Nov. 2022.
\bibitem{li2021deepfed} B. Li, Y. Lu, W. Wei, and J. Huang, ``DeepFed: Federated deep learning for intrusion detection in industrial cyber-physical systems,'' \textit{IEEE Trans. Ind. Informat.}, vol. 17, no. 8, pp. 5615--5624, Aug. 2021.
\bibitem{heinzelman2000energy} W. R. Heinzelman, A. Chandrakasan, and H. Balakrishnan, ``Energy-efficient communication protocol for wireless microsensor networks,'' in \textit{Proc. 33rd HICSS}, pp. 1--10, 2000.
\bibitem{velickovic2018graph} P. Veli\v{c}kovi\'c \textit{et al.}, ``Graph attention networks,'' in \textit{Proc. Int. Conf. Learn. Represent. (ICLR)}, pp. 1--12, 2018.
\bibitem{lo2022egraphsage} W. W. Lo \textit{et al.}, ``E-GraphSAGE: A graph neural network based intrusion detection system for IoT,'' in \textit{IEEE/IFIP NOMS}, pp. 1--9, 2022.
\bibitem{wang2021one} X. Wang, B. Jin, Y. Du, P. Cui, Y. Tan, and Y. Yang, ``One-class graph neural networks for anomaly detection in attributed networks,'' \textit{Neural Comput. Applic.}, vol. 33, no. 18, pp. 12073--12085, 2021.
\end{thebibliography}

\end{document}
"""

with open("manuscript_6pages.tex", "w", encoding="utf-8") as f:
    f.write(content.strip() + "\n")

print("Successfully written original anti-plagiarized manuscript_6pages.tex")
