import re

# Reconstruct from exact logged lines of view_file
# Lines 1 to 120, 121 to 250, 251 to 411 from previous tool outputs

lines_1_to_120 = """\\documentclass[conference]{IEEEtran}
\\IEEEoverridecommandlockouts

\\usepackage{cite}
\\usepackage{amsmath,amssymb,amsfonts}
\\usepackage{algorithm}
\\usepackage{algorithmic}
\\usepackage{graphicx}
\\usepackage{textcomp}
\\usepackage{xcolor}
\\usepackage{booktabs}
\\usepackage{subcaption}
\\usepackage{microtype}
\\usepackage{url}
\\usepackage{balance}

\\setlength{\\abovedisplayskip}{2.0pt plus 1pt minus 1pt}
\\setlength{\\belowdisplayskip}{2.0pt plus 1pt minus 1pt}
\\setlength{\\abovedisplayshortskip}{1.0pt plus 1pt minus 1pt}
\\setlength{\\belowdisplayshortskip}{1.0pt plus 1pt minus 1pt}
\\setlength{\\textfloatsep}{3.0pt plus 1pt minus 1pt}
\\setlength{\\floatsep}{2.5pt plus 1pt minus 1pt}
\\setlength{\\intextsep}{2.5pt plus 1pt minus 1pt}
\\setlength{\\abovecaptionskip}{1.8pt}
\\setlength{\\belowcaptionskip}{0.8pt}

\\def\\BibTeX{{\\rm B\\kern-.05em{\\sc i\\kern-.025em b}\\kern-.08em
    T\\kern-.1667em\\lower.7ex\\hbox{E}\\kern-.125emX}}

\\title{Autonomous Cyber-Resilience and Digital Twin Self-Healing for Resource-Constrained IoT Networks: An Asymptotic and Empirical Investigation}

\\author{}

\\setcounter{topnumber}{4}
\\setcounter{bottomnumber}{4}
\\setcounter{totalnumber}{6}
\\setcounter{dbltopnumber}{3}
\\renewcommand{\\topfraction}{0.95}
\\renewcommand{\\textfraction}{0.05}
\\renewcommand{\\floatpagefraction}{0.85}
\\renewcommand{\\dbltopfraction}{0.95}
\\renewcommand{\\dblfloatpagefraction}{0.85}

\\begin{document}

\\maketitle

\\begin{abstract}
Resource-constrained Internet of Things (IoT) sensor networks are vulnerable to denial-of-service, selective grayhole, and evasive on-off cyberattacks. Conventional intrusion response systems isolate suspect nodes via rigid heuristics; however, in sparse or tree topologies, isolating articulation points (cut-vertices) severely partitions the network graph, stranding downstream sensors. To address this issue, this paper presents an autonomous, closed-loop digital twin self-healing architecture. The framework synchronizes physical telemetry into an in-silico graph shadow, computes asymmetric Bayesian-inspired trust with cut-vertex awareness, and forward-projects candidate mitigations across dual lookahead horizons ($H=30$\\,s for gateways; $H=10$\\,s for microcontrollers) within a sandboxed simulation engine. Multi-objective TOPSIS balances delivery ratio, energy, latency, and queue stability, while dynamic Wald Sequential Probability Ratio Testing (SPRT) reduces post-actuation verification delay by $\\approx 75\\%$ with sub-millisecond state-consistent snapshot restoration. Across 120 matched scenarios $\\times$ 5 strategies (600 runs covering 4 threat classes), the policy achieves a $0.00\\%$ observed partition rate under articulation-aware action constraints ($0.00\\%$ median vs. $72.50\\%$ in Baseline~2: Static IDS). Supporting evaluations show that minimax defense preserves $91.67\\%$ accuracy under PGD-10 evasion, while federated edge coordination reduces uplink traffic by $87.5\\%$ under differential privacy. Empirical scaling closely follows the derived $\\mathcal{O}(N)$ complexity ($R^2 = 0.9953$), meeting the 500-ms cycle deadline under projected ESP32-S3 execution ($350.5 \\pm 8.4$\\,ms).
\\end{abstract}

\\begin{IEEEkeywords}
Digital Twin, Cyber-Resilience, Self-Healing, IoT Security, Graph Neural Networks, Adversarial Robustness, Federated Learning, Wald SPRT, Multi-Objective Optimization.
\\end{IEEEkeywords}

\\section{Introduction}
Mission-critical Internet of Things (IoT) deployments operate under strict hardware limits: microcontrollers clocked at 16--240\\,MHz, constrained RAM (16\\,KB--8\\,MB), and finite battery reserves. Multi-hop wireless propagation creates an expansive attack surface vulnerable to denial-of-service (DoS) flooding, grayhole packet dropping, and evasive on-off cycling \\cite{yigit2024ai, mani2023machine, ge2024gazeta, li2021deepfed}.

When intrusions occur, conventional automated intrusion response systems (IRS) typically quarantine suspect nodes immediately \\cite{mani2023machine, ge2024gazeta, yang2024enabling, liu2022selfhealing}. However, an unintended consequence of automated quarantine is the cut-vertex partitioning problem. In multi-hop wireless topologies, intermediate forwarding relays frequently act as articulation points whose removal splits the connected graph into disjoint components. Quarantining a compromised cut-vertex severs communication paths to downstream clusters, stranding up to 48.2\\% of legitimate nodes. In sensing networks, such collateral disconnection can cause service disruptions comparable to the intrusion itself.

\\begin{figure*}[t]
\\centering
\\includegraphics[width=0.98\\textwidth]{plots/fig1_flowchart_vector_tight.pdf}
\\caption{Closed-loop Digital Twin Self-Healing architecture, detailing continuous operational synchronization across the Physical IoT Layer, Digital Twin Virtual Shadow, In-Silico Predictive Sandbox, Multi-Objective TOPSIS Selection, and Dynamic Wald SPRT Actuation/Rollback Loop.}
\\label{fig:system_architecture}
\\end{figure*}

\\subsection{Related Works}
Digital twins (DTs) and Graph Neural Networks (GNNs) have shown promise for relational IoT anomaly detection \\cite{debenedictis2023digital, khan2022digital, jia2023virtual, lo2022egraphsage, wang2021one, velickovic2018graph}. However, existing approaches exhibit three principal limitations: (i)~a lack of topological awareness during node isolation, causing severe network partitioning \\cite{mani2023machine, liu2024region}; (ii)~direct physical actuation without prior simulation, which risks secondary routing loops and buffer saturation \\cite{yang2024enabling, sood2023intrusion, wu2023heterogeneous}; and (iii)~lengthy verification intervals ($W \\ge 15$\\,s) that lack automated rollback capabilities \\cite{upadhyaya2021multihypothesis, kouicem2022decentralized}.

\\subsection{Key Contributions}
This paper presents a topology-aware digital twin self-healing framework for resource-constrained IoT networks, structured around four primary mechanisms:
\\begin{itemize}
\\setlength{\\itemsep}{0.5pt}
\\setlength{\\parskip}{0pt}
    \\item \\textit{Topology-aware trust estimation:} Combines Spatio-Temporal GAT with asymmetric Bayesian-inspired trust updates and Tarjan cut-vertex discovery, eliminating partition collapse under articulation-aware constraints ($0.00\\%$ median vs. $72.50\\%$ in Baseline~2).
    \\item \\textit{Lookahead sandbox simulation:} Projects candidate mitigations across dual horizons ($H=30$\\,s for gateways; $H=10$\\,s for microcontrollers) in a discrete-event sandbox, ranking actions via multi-objective TOPSIS over PDR, energy, latency, and queue backlog.
    \\item \\textit{Sequential verification and state rollback:} Employs Wald SPRT to reduce verification delay by $\\approx 75\\%$, backed by cryptographic state snapshots enabling sub-millisecond restoration ($<0.1$\\,ms) if an anomaly persists.
    \\item \\textit{Edge scalability and adversarial robustness:} Incorporates minimax PGD defense and FedGraphBridge federated edge coordination, reducing uplink communication by $87.5\\%$ under differential privacy and exhibiting $\\mathcal{O}(N)$ scaling within a 500-ms edge execution budget.
\\end{itemize}

\\section{System Model and Threat Formulation}
\\label{sec:system_model}

\\subsection{Physical IoT Network and Twin Shadow Model}
We model the sensor network as a directed graph $G_{\\text{phy}}(t) = (V, E_{\\text{phy}}(t))$ with $N$ nodes $V$ and active links $E_{\\text{phy}}(t)$. Path loss obeys $\\text{PL}(d) = \\text{PL}(d_0) + 10 \\eta \\log_{10}(d/d_0) + X_\\sigma$ ($X_\\sigma \\sim \\mathcal{N}(0, \\sigma^2)$). Link delivery probability $p_{ij}$ follows SINR thresholding:
\\begin{equation}
\\label{eq:link_success}
p_{ij} = [1 - \\tfrac{1}{2} \\exp(-\\gamma_{ij}/2)]^{8 L_p}, \\quad \\gamma_{ij} = \\frac{P_t h_{ij}}{N_0 + \\sum_{k \\ne i} P_k h_{kj}},
\\end{equation}
with radio dissipation $E_{\\text{tx}}(l, d) = l E_{\\text{elec}} + l \\epsilon_{\\text{amp}} d^\\eta$ and $E_{\\text{rx}}(l) = l E_{\\text{elec}}$ \\cite{heinzelman2000energy}. The digital twin maintains an in-silico shadow $G_{\\text{twin}}(t) = (V, E_{\\text{twin}}(t))$ synchronized via periodic telemetry ingestion, tracking packet forwarding, queue backlogs, battery state, and active routing topology. Fig.~\\ref{fig:node_topology}(a) illustrates a nominal mesh highlighting articulation points (cut-vertices).

\\begin{figure*}[t]
\\centering
\\includegraphics[width=0.98\\textwidth]{plots/fig2_node_topology_tight.pdf}
\\caption{Multi-hop IoT node connectivity and autonomous topological self-healing. (a)~Nominal 6-node mesh highlighting Tarjan cut-vertex (articulation point) $v_4$ ($\\delta_{\\text{cut}} = 1$); (b)~Active cyberattack on node $v_2$ injecting buffer flooding and selective packet dropping; (c)~Closed-loop self-healing executing loop-free BFS bypass detour $s_{\\text{bypass}}$, RF power boost ($+3$\\,dBm), and ingress rate clamping, preventing network partitioning without isolating critical articulation nodes.}
\\label{fig:node_topology}
\\end{figure*}

\\begin{table}[t]
\\centering
\\caption{Simulation Environment and Network Model Parameters}
\\label{tab:simulation_specs}
\\footnotesize
\\renewcommand{\\arraystretch}{1.10}
\\setlength{\\tabcolsep}{4.0pt}
\\begin{tabular}{|l|r|}
\\hline
\\textbf{System Parameter} & \\textbf{Nominal Value / Sweep Range} \\\\
\\hline
Network Scale ($N$) & 24 nodes (Scalability: 6--100) \\\\
\\hline
Simulation Duration ($T$) & 80.0\\,s per episode \\\\
\\hline
Telemetry Sampling ($\\Delta t$) & 0.33\\,s (3\\,Hz ingestion rate) \\\\
\\hline
Decision Window ($W$) & 10 frames (3.33\\,s window) \\\\
\\hline
Nominal Traffic Rate ($\\lambda$) & 2.0\\,pkts/s (Poisson process) \\\\
\\hline"""

lines_121_to_250 = """Packet Payload Size ($L_p$) & 64\\,bytes (IEEE 802.15.4 frame) \\\\
\\hline
Queue Capacity ($B_{\\max}$) & 100\\,packets (Drop-tail discipline) \\\\
\\hline
Channel Path Loss ($\\eta, \\sigma$) & $\\eta = 2.8$, shadow fading $\\sigma = 3.5$\\,dB \\\\
\\hline
RF Step-Up Power Boost & $+3$\\,dBm transmission gain \\\\
\\hline
Attack Window & Active $t \\in [20, 60]$\\,s \\\\
\\hline
Evaluated Threat Vectors & DoS, Grayhole, Outage, On-Off \\\\
\\hline
Evaluated Strategy Runs & 120 scenarios $\\times$ 5 strategies = 600 \\\\
\\hline
\\end{tabular}
\\end{table}

\\subsection{Simulation Setup and GNN Training Configuration}
Table~\\ref{tab:simulation_specs} summarizes parameters. Sampling at 3\\,Hz consumes $0.61\\%$ bandwidth ($0.042$\\,mJ/frame).
\\textit{GNN architecture and training:} The detector processes 12 node features (traffic rates, loss, latency, queue depth, energy, CPU load, forwarding ratios, loss variance, state transitions, degree, cut-vertex flag $\\delta_{\\text{cut}}$, and betweenness centrality) and 4 edge features. A 2-layer BridgeAwareGAT ($12 \\to 64$ with 4 heads $\\to 32$, bridge penalty $\\gamma=0.5$) and 1-layer GRU ($32 \\to 32$, window $W=5$) feed dual MLP heads for 5-class anomaly classification ($\\mathcal{L}_{\\text{CE}}$) and continuous trust regression ($\\mathcal{L}_{\\text{MSE}}$). Multi-task training minimizes $\\mathcal{L} = 0.65\\mathcal{L}_{\\text{CE}} + 0.35\\mathcal{L}_{\\text{MSE}}$ via Adam ($\\text{lr}=3\\times 10^{-4}$, weight decay $10^{-4}$) with CosineAnnealingLR ($T_{\\max}=50$) over 50 epochs (batch size 64, 31,500 snapshots across 30 seeds). An 80/20 train/test split across disjoint seeds and attack paths (zero temporal leakage; 115,200 windows) yields $99.96\\%$ accuracy ($100\\%$ precision, $99.97\\%$ recall).

\\subsection{Adversarial Threat Models and Attack Functions}
We evaluate four threat classes: (i)~Type~1 (DoS flooding): an attacker node $v_a$ injects traffic at rate $\\lambda_{\\text{flood}} = 25\\,\\text{pkts/s} \\gg \\lambda_{\\text{nominal}}$, causing queue buffer overflow; (ii)~Type~2 (selective grayhole): drops packets probabilistically with $p_{\\text{drop}} \\in [0.4, 0.8]$ while transmitting routing heartbeats; (iii)~Type~3 (crash outage): complete node failure removing incident edges $E(t) \\leftarrow E(t) \\setminus \\{(v_a, v_j) \\mid v_j \\in \\mathcal{N}(v_a)\\}$; and (iv)~Type~4 (on-off evasion): alternates between packet dropping ($T_{\\text{attack}} = 10$\\,s) and normal operation ($T_{\\text{dormant}} = 15$\\,s) to exploit symmetric trust recovery.

\\section{Closed-Loop Digital Twin Architecture}
\\label{sec:architecture}
As shown in Fig.~\\ref{fig:system_architecture}, the closed-loop architecture operates across five core functional modules.

\\subsection{Articulation-Aware Bayesian-Inspired Trust and Topological Criticality}
The digital twin maintains a continuous Bayesian-inspired trust score $\\mathcal{T}_i(t) \\in [0, 1]$ for each node $i \\in V$. Forwarding fidelity $\\mathcal{T}_{\\text{fwd}}$ and loss rate $\\mathcal{T}_{\\text{loss}}$ follow Beta-binomial conjugate observation updates ($\\mathbb{E}[\\theta] = \\frac{\\alpha}{\\alpha+\\beta}$ under prior $\\text{Beta}(1, 1)$), aggregated with energy $\\mathcal{T}_{\\text{energy}}$ and ML score $\\mathcal{T}_{\\text{ml}}$:
\\begin{equation}
\\label{eq:bayesian_inst}
\\mathcal{T}_{\\text{inst}, i}(t) = w_f \\mathcal{T}_{\\text{fwd}, i} + w_e \\mathcal{T}_{\\text{energy}, i} + w_l \\mathcal{T}_{\\text{loss}, i} + w_m \\mathcal{T}_{\\text{ml}, i},
\\end{equation}
with normalized weights $\\mathbf{w} = [0.35, 0.20, 0.25, 0.20]$. To counter periodic on-off evasion, trust updates follow asymmetric temporal exponential smoothing:
\\begin{equation}
\\label{eq:asym_trust}
\\mathcal{T}_i(t) = \\begin{cases}
(1 - \\lambda_p)\\mathcal{T}_i(t-1) + \\lambda_p \\mathcal{T}_{\\text{inst}, i}, & \\mathcal{T}_{\\text{inst}, i} < \\mathcal{T}_i(t-1), \\\\
(1 - \\lambda_r)\\mathcal{T}_i(t-1) + \\lambda_r \\mathcal{T}_{\\text{inst}, i}, & \\text{otherwise},
\\end{cases}
\\end{equation}
where penalty parameter $\\lambda_p = 0.40$ and recovery parameter $\\lambda_r = 0.05$ enforce an 8:1 penalty-to-recovery asymmetry.

\\textbf{Theorem 1 (Steady-State Trust Bound Under On-Off Evasion)}: \\textit{For an on-off adversary attacking with duty cycle $\\rho \\in (0, 1)$ between dropping ($\\mathcal{T}_{\\min}$) and compliance ($\\mathcal{T}_{\\max}$), a sufficient condition for steady-state trust suppression below threshold $\\tau_{\\text{thresh}}$ ($\\lim_{t\\to\\infty} \\mathcal{T}_i(t) < \\tau_{\\text{thresh}}$) is:}
\\begin{equation}
\\label{eq:evasion_bound}
\\frac{\\lambda_p}{\\lambda_r} > \\left(\\frac{1 - \\rho}{\\rho}\\right) \\left(\\frac{\\mathcal{T}_{\\max} - \\tau_{\\text{thresh}}}{\\tau_{\\text{thresh}} - \\mathcal{T}_{\\min}}\\right).
\\end{equation}
\\textit{Proof}: Net drift satisfies $\\Delta \\mathcal{T} = \\rho T [-\\lambda_p(\\tau_{\\text{thresh}} - \\mathcal{T}_{\\min})] + (1 - \\rho) T [\\lambda_r(\\mathcal{T}_{\\max} - \\tau_{\\text{thresh}})] < 0$, yielding \\eqref{eq:evasion_bound}. For $\\tau_{\\text{thresh}} = 0.50$, $\\mathcal{T}_{\\max} = 1.0$, $\\mathcal{T}_{\\min} \\le 0.10$, and $\\rho \\ge 0.20$, RHS evaluates to $\\le 5.0$. Calibrated ratio $\\lambda_p / \\lambda_r = 0.40 / 0.05 = 8.0 > 5.0$ guarantees steady-state trust suppression below $\\tau_{\\text{thresh}}$. $\\blacksquare$

Topological criticality $C_i \\in [0.10, 1.00]$ combines betweenness $B(i)$, degree $D(i)$, and cut-vertex flag $\\delta_{\\text{cut}}(i)$:
\\begin{equation}
\\label{eq:criticality}
C_i = 0.10 + 0.90 \\cdot [w_b B(i) + w_d D(i) + \\delta_{\\text{cut}}(i) \\cdot \\alpha_{\\text{boost}}],
\\end{equation}
where $\\delta_{\\text{cut}}(i) = 1$ if node $i$ is an articulation point of $G(t)$, computed via Tarjan DFS in $\\mathcal{O}(|V| + |E|)$ time ($\\alpha_{\\text{boost}} = 0.50$). When trust falls below $\\tau_{\\text{thresh}} = 0.50$, self-healing triggers (Algorithm~1). As in Fig.~\\ref{fig:node_topology}(b)-(c), hard quarantine is barred for articulation nodes ($\\delta_{\\text{cut}} = 1$); BFS detours and rate-clamping are prioritized instead.

\\subsection{In-Silico Sandbox Simulation and TOPSIS Optimization}
The twin synthesizes candidate actions $\\mathcal{S} = \\{s_1, \\dots, s_K\\}$: $s_{\\text{bypass}}$ (loop-free BFS detour), $s_{\\text{rate}}$ (token rate clamping at $0.5\\,\\text{pkts/s}$), $s_{\\text{power}}$ (RF step-up $+3\\,\\text{dBm}$), and $s_{\\text{quarantine}}$ (isolation, barred if $\\delta_{\\text{cut}} = 1$). Candidates are forward-projected across horizon $H$ in a discrete-event sandbox: (i)~a gateway profile ($H=30$\\,s, $\\text{RMSE}=0.024$, $6.5$\\,ms) for edge computers running continuous synchronization; and (ii)~an edge microcontroller profile ($H=10$\\,s, $\\text{RMSE}=0.058$, $2.28$\\,ms) suitable for constrained nodes. Matrix $\\mathbf{X} = [x_{km}]_{K \\times 4}$ captures PDR ($f_{\\text{PDR}}$), energy ($f_{\\text{eng}}$), latency ($f_{\\text{lat}}$), and queue stability ($f_{\\text{queue}}$). TOPSIS ranks actions via closeness score $\\Phi(s_k)$:
\\begin{equation}
\\label{eq:topsis}
\\Phi(s_k) = \\frac{D^-(s_k)}{D^+(s_k) + D^-(s_k)}, \\quad s^* = \\arg\\max_{s_k \\in \\mathcal{S}} \\Phi(s_k).
\\end{equation}

\\textbf{Theorem 2 (Conditional Connectivity Under Feasible Detours)}: \\textit{Let $G$ be connected. For any non-articulation node $v \\notin V_{\\text{cut}}$, the subgraph $G \\setminus \\{v\\}$ remains connected by definition. For any articulation node $v_a \\in V_{\\text{cut}}$, where hard quarantine is barred ($\\delta_{\\text{cut}}(v_a) = 1 \\implies s_{\\text{quarantine}} \\notin \\mathcal{S}$), if the selected mitigation provides a feasible positive-conductance detour connecting its separated components, post-actuation algebraic connectivity satisfies $\\lambda_2(L') > 0$. If dense cut-chains leave no feasible detour, connectivity preservation is conditional.}
\\textit{Proof}: Isolating a non-cut node leaves $G \\setminus \\{v\\}$ connected by definition. For articulation nodes ($\\delta_{\\text{cut}}(v_a)=1$), hard quarantine is barred ($s_{\\text{quarantine}} \\notin \\mathcal{S}$), restricting actuation to rate-clamping ($s_{\\text{rate}}$) and BFS detours ($s_{\\text{bypass}}$). Under the conditional premise that an alternate detour of positive conductance ($c_{\\text{detour}} > 0$) exists, the post-actuation graph preserves a spanning tree across all non-faulty nodes. By spectral graph theory, a graph is connected iff $\\lambda_2(L') > 0$, guaranteeing algebraic connectivity. $\\blacksquare$

\\subsection{Dynamic Wald SPRT Verification and Safety Rollback}
To evaluate post-mitigation recovery without imposing arbitrary fixed observation windows, observations accumulate log-likelihood ratios over packet loss rates under $H_0$ (nominal loss $p_0 = 0.03$) and $H_1$ (degraded loss $p_1 = 0.12$) with weight $n_{\\text{eff}}=5$ \\cite{upadhyaya2021multihypothesis}:
\\begin{equation}
\\label{eq:wald}
\\Lambda_m = \\sum_{k=1}^m \\Delta \\Lambda_k = d_m \\ln\\frac{p_1}{p_0} + (m \\cdot n_{\\text{eff}} - d_m) \\ln\\frac{1 - p_1}{1 - p_0},
\\end{equation}
where $d_m$ counts dropped packets across $m$ steps. Decision boundaries with error bounds $\\alpha_{\\text{sprt}} = 0.01$ and $\\beta_{\\text{sprt}} = 0.05$ are $A = \\ln\\frac{1-\\beta_{\\text{sprt}}}{\\alpha_{\\text{sprt}}} \\approx 4.554$ and $B = \\ln\\frac{\\beta_{\\text{sprt}}}{1-\\alpha_{\\text{sprt}}} \\approx -2.986$. Sequential testing terminates when $\\Lambda_m \\le B$ (accepting $H_0$, recovery certified) or $\\Lambda_m \\ge A$ (accepting $H_1$, persistent failure). If $\Lambda_m \\ge A$ or $k(G') < 1$, pre-actuation snapshot $\\mathcal{S}_{\\text{pre}}$ is restored in $<0.1$\\,ms (state-consistent memory rollback verified via SHA-256 integrity hash, distinct from end-to-end MTTR $= 4.50$\\,s including SPRT sampling).

\\textbf{Proposition 1 (Average Sample Number Bound)}: \\textit{Under $H_0$, the Wald SPRT expected sample size to reach boundary $B$ is bounded by $\\mathbb{E}_0[N] \\approx \\frac{(1 - \\alpha_{\\text{sprt}}) B + \\alpha_{\\text{sprt}} A}{\\mathbb{E}_0[\\Delta \\Lambda]} \\approx 11.0\\text{ frames}$ ($3.67$\\,s at 3\\,Hz; empirical mean $9.3\\text{--}10.5\\text{ frames}$ / $3.1\\text{--}3.5$\\,s), nesting inside end-to-end MTTR ($4.50$\\,s) and reducing verification delay by $\\approx 75\\%$ compared to static 15\\,s windows.}

\\textbf{Theorem 3 (Foster-Lyapunov Queue Stability)}: \\textit{Under rate clamping $s_{\\text{rate}}$ with arrival $\\lambda_a \\le \\mu_a - \\epsilon$ ($\\epsilon > 0$), quadratic backlog $V(\\mathbf{q}(t)) = \\frac{1}{2} \\sum_{i \\in V} q_i(t)^2$ satisfies negative drift $\\mathbb{E}[\\Delta V(\\mathbf{q}(t)) \\mid \\mathbf{q}(t)] \\le B - \\epsilon \\sum_{i \\in V} q_i(t)$, where $B = \\frac{1}{2}\\sum_i (\\lambda_i^2 + \\mu_i^2) < \\infty$, bounding mean backlogs $\\limsup_{T \\to \\infty} \\frac{1}{T} \\sum_{t=0}^{T-1} \\sum_i \\mathbb{E}[q_i(t)] \\le B/\\epsilon < \\infty$ and precluding buffer overflow.}

\\textbf{Proposition 2 (Empirical Detection Latency Reduction)}: \\textit{Let $\\mathcal{T}_i^{\\text{fused}}(t) = \\beta_i \\mathcal{T}_i^{\\text{Bayes}}(t) + (1-\\beta_i)\\mathcal{T}_i^{\\text{GNN}}(t)$ denote the fused trust estimator ($\\beta_{\\text{cut}}=0.35, \\beta_{\\text{leaf}}=0.60$). In our evaluated topology, spatial GAT message aggregation across 2-hop neighborhoods reduces median detection latency by $2.1\\times$ relative to local Bayesian estimation ($2.10$\\,s vs. $4.41$\\,s; Wilcoxon $W=14.0, p < 10^{-4}$), accelerating anomaly discovery without destabilizing asymptotic trust updates.}

\\begin{table*}[t]
\\centering
\\caption{Comparative Benchmarks Across Mitigation Strategies Under Cyberattacks ($n=120$ Matched Scenarios, 600 Total Runs, Mean $\\pm$ SD and Median [IQR]).}
\\label{tab:comparative_benchmarks}
\\footnotesize
\\renewcommand{\\arraystretch}{1.12}
\\setlength{\\tabcolsep}{1.40pt}
\\begin{tabular}{|l|c|c|c|c|c|c|c|}
\\hline
\\textbf{Mitigation Scheme} & \\textbf{Resilience $\\mathcal{R}$} & \\textbf{Mean PDR} & \\textbf{Nadir PDR} & \\textbf{Part. Mean} & \\textbf{Med. [IQR]} & \\textbf{Energy (J)} & \\textbf{MTTR (s)} \\\\
\\hline
Baseline 1: Unmitigated & $0.7976 \\pm 0.018$ & $0.7812 \\pm 0.021$ & $0.6240 \\pm 0.035$ & $0.00 \\pm 0.00\\%$ & $0.00 [0.00]\\%$ & $38.42 \\pm 1.25$ & $\\infty$ (No rec.) \\\\
\\hline
Baseline 2: Static IDS \\cite{mani2023machine}$^\\dagger$ & $0.7512 \\pm 0.034$ & $0.7420 \\pm 0.041$ & $0.5180 \\pm 0.062$ & $54.20 \\pm 31.43\\%$ & $72.50 [21.87]\\%$ & $36.18 \\pm 1.10$ & $18.40 \\pm 2.15$ \\\\
\\hline
Baseline 3: ML Heuristic \\cite{yigit2024ai}$^\\dagger$ & $0.8325 \\pm 0.015$ & $0.8240 \\pm 0.019$ & $0.6890 \\pm 0.028$ & $14.25 \\pm 2.65\\%$ & $14.50 [0.00]\\%$ & $34.80 \\pm 0.95$ & $14.20 \\pm 1.80$ \\\\
\\hline
Baseline 4: Standalone GNN \\cite{lo2022egraphsage}$^\\dagger$ & $0.7845 \\pm 0.024$ & $0.8520 \\pm 0.028$ & $0.5840 \\pm 0.045$ & $46.88 \\pm 27.06\\%$ & $62.50 [31.25]\\%$ & $35.40 \\pm 1.05$ & $15.80 \\pm 2.10$ \\\\
\\hline
\\textbf{Proposed: GNN-Fused Twin} & $\\mathbf{0.9380 \\pm 0.009}$ & $\\mathbf{0.9550 \\pm 0.008}$ & $\\mathbf{0.8350 \\pm 0.018}$ & $\\mathbf{0.00 \\pm 0.00\\%}$ & $\\mathbf{0.00 [0.00]\\%}$ & $\\mathbf{30.85 \\pm 0.75}$ & $\\mathbf{4.50 \\pm 0.60}$ \\\\
\\hline
\\multicolumn{8}{|p{\\dimexpr\\textwidth-2\\tabcolsep-2\\arrayrulewidth\\relax}|}{\\scriptsize \\textbf{Type 4 On-Off Evasion:} Baseline 2 triggers $72.42 \\pm 0.85\\%$ partition ($72.50\\%$ median); Baseline 4 triggers $62.50\\%$ median; Proposed sustains $0.00\\%$ partition and $\\mathcal{R} = 0.9385 \\pm 0.010$.} \\\\
\\hline
\\multicolumn{8}{|p{\\dimexpr\\textwidth-2\\tabcolsep-2\\arrayrulewidth\\relax}|}{\\scriptsize \\textbf{Inferential Statistics (Proposed vs. B2, $n=120$):} Paired diff $= 54.20 \\pm 31.43$\\,pp ($95\\%$ CI $[48.57, 59.82]$); $t(119)=18.89, p=1.29 \\times 10^{-37}$; Wilcoxon $W=0.0$; Cohen's $d=1.724$.} \\\\
\\hline
\\end{tabular}
\\end{table*}

\\begin{algorithm}[t]
\\caption{Closed-Loop Digital Twin Self-Healing \\& Verification}
\\label{alg:self_healing}
\\begin{algorithmic}[1]
\\footnotesize
\\REQUIRE Telemetry frame $\\mathbf{z}(t)$, Topology graph $G(t)$, Prior snapshot $\\mathcal{S}_{\\text{pre}}$
\\ENSURE Actuation policy $s^*$, Verification state $\\mathcal{V}$
\\STATE Synchronize twin state: $G_{\\text{twin}}(t) \\leftarrow \\text{Sync}(G(t), \\mathbf{z}(t))$
\\STATE Detect articulation points: $\\Delta_{\\text{cut}} \\leftarrow \\text{TarjanCutVertices}(G_{\\text{twin}})$
\\STATE Compute fused GNN-Bayesian trust $\\mathcal{T}_i^{\\text{fused}}(t)$ and criticality $C_i(t)$
\\IF{$\\exists i \\in V \\text{ s.t. } \\mathcal{T}_i^{\\text{fused}}(t) < \\tau_{\\text{thresh}}$}
    \\STATE Capture integrity-verified snapshot: $\\mathcal{S}_{\\text{pre}} \\leftarrow \\text{CaptureSnapshot}(G_{\\text{twin}})$
    \\STATE Generate candidate pool $\\mathcal{S} \\leftarrow \\text{SynthesizeActions}(i, \\Delta_{\\text{cut}})$
    \\FORALL{$s \\in \\mathcal{S}$}
        \\STATE Project forward $H$ in sandbox (30\\,s gateway / 10\\,s MCU): $\\hat{\\mathbf{x}}_s \\leftarrow \\text{Simulate}(G_{\\text{twin}}, s, H)$
    \\ENDFOR
    \\STATE Select multi-objective policy: $s^* \\leftarrow \\arg\\max_{s} \\Phi(s)$ via TOPSIS \\eqref{eq:topsis}
    \\STATE Dispatch signed actuation command $s^*$ to physical nodes
    \\STATE Initialize Wald SPRT log-likelihood accumulator: $\\Lambda_0 \\leftarrow 0$
    \\REPEAT"""

lines_251_to_411 = """        \\STATE Collect post-actuation sample $x_m$; update $\\Lambda_m$ via \\eqref{eq:wald}
    \\UNTIL{$\\Lambda_m \\le B$ (Accept $H_0$) \\textbf{or} $\\Lambda_m \\ge A$ (Accept $H_1$)}
    \\IF{$\\Lambda_m \\ge A$ \\textbf{or} PartitionDetected()}
        \\STATE Execute state-consistent rollback: $\\text{RollbackTo}(\\mathcal{S}_{\\text{pre}})$
        \\STATE $\\mathcal{V} \\leftarrow \\text{SAFETY\\_ROLLBACK}$
    \\ELSE
        \\STATE $\\mathcal{V} \\leftarrow \\text{VERIFIED\\_RECOVERY}$
    \\ENDIF
\\ENDIF
\\end{algorithmic}
\\end{algorithm}

\\noindent \\textit{Telemetry streaming and monitoring}: An operator interface ingests telemetry at 3\\,Hz over WebSockets, displaying real-time delivery ratio ($97.9\\%$), latency ($26.5\\,\\text{ms}$), identified articulation points, and mitigation states.

\\begin{figure}[t]
\\centering
\\includegraphics[width=\\columnwidth]{plots/fig3_column_resilience_partition.pdf}
\\caption{Dynamic cyber-resilience benchmarks across $n=120$ matched scenarios: (a) Dynamic resilience trajectory $Q(t)$ under cut-vertex intrusion; (b) Network partition rate comparison across threat vectors.}
\\label{fig:phase11_results}
\\end{figure}

\\begin{figure}[t]
\\centering
\\includegraphics[width=\\columnwidth]{plots/fig4_column_parameter_sensitivity.pdf}
\\caption{Parameter sensitivity analysis: (a) In-silico lookahead horizon $H$ trade-off; (b) Downlink tolerance under lossy wireless channels.}
\\label{fig:ablation_results}
\\end{figure}

\\section{Experimental Evaluation and Result Discussion}
\\label{sec:experiments}
We evaluate empirical cyber-resilience, topological partition avoidance, and inferential statistics across 600 total simulation runs (120 matched scenario instances evaluated across five mitigation strategies).

\\subsection{Evaluation Metrics and Baseline Parity}
Metrics comprise: (i)~Mean PDR $\\bar{\\text{PDR}} = \\frac{1}{T}\\sum_{t=1}^T \\text{PDR}(t)$ over the full 80\\,s episode; (ii)~Nadir PDR $\\min_t \\text{PDR}(t)$ capturing minimum instantaneous packet delivery during transient attack/quarantine collapse; (iii)~Partition Rate (\\% stranded nodes); (iv)~Resilience Score $\\mathcal{R} = \\frac{1}{t_r - t_0} \\int_{t_0}^{t_r} Q(t) \\, dt$; (v)~MTTR until SPRT certification; and (vi)~Cumulative energy (J).

Scenarios span 30 random seeds ($S \\in \\{42, \\dots, 71\\}$) and four threat vectors under Poisson traffic over $T=80$\\,s. Baselines 2 \\cite{mani2023machine}, 3 \\cite{yigit2024ai}, and 4 \\cite{lo2022egraphsage} are adapted from published specifications under identical channel and traffic profiles.

\\subsection{Benchmark Performance and Partition Avoidance}
As summarized in Table~\\ref{tab:comparative_benchmarks}, the proposed architecture achieves a resilience score of $\\mathcal{R} = 0.9380 \\pm 0.009$ (a 24.9\\% gain over Baseline~2 and 12.7\\% over Baseline~3) while maintaining a nadir PDR of $83.5 \\pm 1.8\\%$ (compared to $51.8 \\pm 6.2\\%$; Fig.~\\ref{fig:phase11_results}(a)). In Baseline~4, unconstrained cut-vertex quarantine drops instantaneous delivery to a nadir PDR of $0.5840 \\pm 0.045$ with significant partitioning ($46.88 \\pm 27.06\\%$, median $62.50\\%$), although its full-episode Mean PDR averages $0.8520 \\pm 0.028$ due to pre-attack baseline traffic and communication over intact subgraphs. Under articulation-aware action constraints that prevent the quarantine of cut-vertices, the proposed policy achieved a $0.00\\%$ observed partition rate across all evaluated episodes ($0.00\\%$ median; Fig.~\\ref{fig:phase11_results}(b)). Fused trust estimation lowers MTTR to $4.50 \\pm 0.60$\\,s. Lookahead ablation (Fig.~\\ref{fig:ablation_results}(a)) indicates that $H=30$\\,s provides high simulation accuracy for edge gateways ($\\text{RMSE}=0.024$, $6.5$\\,ms), while $H=10$\\,s offers a lightweight profile for microcontrollers ($\\text{RMSE}=0.058$, $2.28$\\,ms). ARQ retransmissions preserve $\\mathcal{R} \\ge 0.80$ under channel loss up to $30\\%$ (Fig.~\\ref{fig:ablation_results}(b)).

\\subsection{Statistical Significance and Component Ablation}
Across $n=120$ matched pairs, the partition reduction over Baseline~2 is $54.20 \\pm 31.43$\\,pp ($95\\%$ CI $[48.57, 59.82]$; paired $t(119) = 18.89, p = 1.29 \\times 10^{-37}$; Wilcoxon $W = 0.0$; Cohen's $d = 1.724$; Bayes factor $BF_{10} = 5.18 \\times 10^{21} \\gg 100$).

\\begin{table}[t]
\\centering
\\caption{Systematic Component Ablation Study ($n=120$ Scenarios: 30 Seeds $\\times$ 4 Threat Classes)}
\\label{tab:ablation_study}
\\footnotesize
\\renewcommand{\\arraystretch}{1.10}
\\setlength{\\tabcolsep}{0.6pt}
\\begin{tabular}{|l|c|c|c|c|}
\\hline
\\textbf{Variant} & $\\mathcal{R}$ & \\textbf{Part.} & \\textbf{MTTR} & \\textbf{Eng. (J)} \\\\
\\hline
\\textbf{Proposed System} & $\\mathbf{0.938 \\pm 0.01}$ & $\\mathbf{0.00\\%}$ & $\\mathbf{4.50 \\pm 0.60}$ & $\\mathbf{30.85 \\pm 0.75}$ \\\\
\\hline
w/o Cut-Vertex Aw. & $0.751 \\pm 0.03$ & $54.20\\%$ & $16.20 \\pm 1.85$ & $36.18 \\pm 1.10$ \\\\
\\hline
w/o Sandbox ($H=0$) & $0.842 \\pm 0.02$ & $12.40\\%$ & $12.80 \\pm 1.40$ & $35.40 \\pm 0.95$ \\\\
\\hline
w/o Wald SPRT & $0.865 \\pm 0.02$ & $0.00\\%$ & $18.40 \\pm 2.15$ & $33.90 \\pm 0.85$ \\\\
\\hline
w/o TOPSIS Opt. & $0.892 \\pm 0.01$ & $0.00\\%$ & $5.10 \\pm 0.70$ & $36.80 \\pm 1.15$ \\\\
\\hline
w/o Heur. Sigs & $0.902 \\pm 0.01$ & $0.00\\%$ & $4.90 \\pm 0.65$ & $31.80 \\pm 0.80$ \\\\
\\hline
\\end{tabular}
\\end{table}

As shown in Table~\\ref{tab:ablation_study}, ablation experiments verify the role of each module. Disabling cut-vertex awareness allows candidate actions to quarantine articulation points, reproducing the partition collapse ($54.20\\%$) and resilience degradation ($\\mathcal{R}=0.7512$) observed in Baseline~2, while retaining SPRT verification ($16.20$\\,s MTTR). Eliminating sandbox lookahead ($H=0$) reduces resilience to $0.8415$, whereas replacing Wald SPRT with fixed 15\\,s observation windows increases MTTR by 155\\% ($18.40$\\,s). Omitting TOPSIS optimization increases energy consumption by 17.8\\% ($36.80$\\,J), while retraining without heuristic signatures maintains $79.7\\%$ binary accuracy with zero-shot generalization across bursty traffic ($80.0\\%$) and Barab\\'{a}si-Albert scale-free graphs ($66.7\\%$).

\\begin{figure}[t]
\\centering
\\includegraphics[width=\\columnwidth]{plots/fig5_adversarial_robustness_clean.pdf}
\\caption{Adversarial evasion robustness under PGD evasion attacks ($L_\\infty$ norm): (a) Classification accuracy vs. perturbation budget $\\epsilon$; (b) Bayesian trust distortion (MAE) under adversarial feature drift.}
\\label{fig:adversarial_results}
\\end{figure}

\\begin{table}[b]
\\centering
\\caption{Adversarial Defense and Federated Edge Learning Benchmarks}
\\label{tab:adversarial_fl_benchmarks}
\\footnotesize
\\renewcommand{\\arraystretch}{1.10}
\\setlength{\\tabcolsep}{2.5pt}
\\begin{tabular}{|l|c|c|c|c|}
\\hline
\\textbf{Defense / FL Scheme} & \\textbf{Acc. (\\%)} & \\textbf{ASR (\\%)} & \\textbf{Trust MAE} & \\textbf{Payload} \\\\
\\hline
Standard GAT (Clean) & $94.20\\%$ & --- & $0.0245$ & $76.8$\\,KB \\\\
\\hline
Standard GAT (PGD-10) & $8.33\\%$ & $95.24\\%$ & $0.5103$ & $76.8$\\,KB \\\\
\\hline
\\textbf{Minimax-Hardened GAT} & $\\mathbf{91.67\\%}$ & $\\mathbf{8.33\\%}$ & $\\mathbf{0.0241}$ & $\\mathbf{76.8\\,\\textbf{KB}}$ \\\\
\\hline
Standard FedAvg ($K=4$) & $78.40\\%$ & --- & $0.0820$ & $76.8$\\,KB \\\\
\\hline
\\textbf{FedGraphBridge + INT8} & $\\mathbf{88.10\\%}$ & --- & $\\mathbf{0.0315}$ & $\\mathbf{9.6\\,\\textbf{KB}}$ \\\\
\\hline
\\end{tabular}
\\end{table}

\\subsection{Adversarial Minimax Defense and Federated Edge Learning}
As shown in Table~\\ref{tab:adversarial_fl_benchmarks}, minimax adversarial training preserves $91.67\\%$ classification accuracy under PGD-10 evasion ($\\epsilon = 0.12$), reducing the attack success rate from $95.24\\%$ to $8.33\\%$ (trust error $\\text{MAE} \\le 0.0241$; Fig.~\\ref{fig:adversarial_results}). Under non-IID Dirichlet partitioning ($\\alpha_{\\text{dir}} = 0.5, K = 4$), FedGraphBridge weights parameter updates by topological centrality, achieving $88.10\\%$ accuracy while reducing uplink data transmission by $87.5\\%$ ($9.6$\\,KB vs. $76.8$\\,KB) under $(\\epsilon=3.2, \\delta=10^{-5})$ differential privacy.

\\begin{figure}[t]
\\centering
\\includegraphics[width=\\columnwidth]{plots/fig6_clean_scalability_hardware.pdf}
\\caption{Asymptotic scalability and edge hardware feasibility: (a) Latency decomposition and linear $\\mathcal{O}(N)$ scaling ($R^2 = 0.9953$); (b) Projected compute latency vs. real-time deadlines across embedded hardware platforms.}
\\label{fig:scalability_results}
\\end{figure}

\\section{Scalability and Edge Hardware Projections}
\\label{sec:scalability}
\\subsection{Asymptotic Complexity Derivation}
Across $N=6$ to $100$ nodes (Fig.~\\ref{fig:scalability_results}(a)), cycle latency decomposes as $\\mathcal{T}_{\\text{cycle}}(N) = \\mathcal{T}_{\\text{sync}} + \\mathcal{T}_{\\text{trust}} + \\mathcal{T}_{\\text{cand}} + \\mathcal{T}_{\\text{sand}} + \\mathcal{T}_{\\text{opt}}$. Sync, trust, and Tarjan discovery scale as $\\mathcal{O}(N)$ for bounded degree, while $|\\mathcal{S}|=4$ actions project in $\\mathcal{O}(1)$ time, closely tracking the derived $\\mathcal{O}(N)$ scaling ($R^2 = 0.9953$; $17.87$\\,ms at $N=6$ to $234.12$\\,ms at $N=100$). Fig.~\\ref{fig:1000_node_topology} illustrates a realistic 1,000-node mesh synthesized from OpenStreetMap residential building coordinates across Dhaka.

\\begin{figure}[t]
\\centering
\\includegraphics[width=\\columnwidth]{plots/fig_1000_nodes_topology_v2_clean.pdf}
\\caption{Realistic 1,000-node IoT topology synthesized from Dhaka residential building coordinates (OpenStreetMap). Blue nodes denote sensors; red nodes denote gateway/transit hubs. Green lines denote local mesh links, orange lines denote backbone trunks, and brown lines denote uplinks.}
\\label{fig:1000_node_topology}
\\end{figure}

\\subsection{Edge Deployment Feasibility and Analytical Scaling}
Compute feasibility across four embedded platforms (Fig.~\\ref{fig:scalability_results}(b)) was evaluated through profiling measurements (100 trials, mean $\\pm$ SD): (i)~Raspberry Pi 4B: $62.3 \\pm 2.1$\\,ms ($\\le 100$\\,ms deadline); (ii)~NVIDIA Jetson Nano: $70.1 \\pm 2.8$\\,ms ($\\le 100$\\,ms); (iii)~Intel Edge: $24.4 \\pm 0.9$\\,ms ($\\le 50$\\,ms); and (iv)~ESP32-S3 (Xtensa LX7, 8\\,MB PSRAM): $350.5 \\pm 8.4$\\,ms ($\\le 500$\\,ms, consuming $<2.5$\\,MB RAM) for the local control loop ($H=10$\\,s lookahead, Tarjan DFS, trust, TOPSIS), satisfying real-time timing deadlines while neural network retraining is offloaded to edge gateways.

\\section{Discussion, Reproducibility, and Conclusion}
\\label{sec:conclusion}
\\noindent\\textit{Threats to Validity:} Evaluation limitations include wireless multipath fading, sparse cut chains stressing detour capacity, collusions of $K > 5$ cut attackers, multi-cluster scaling ($N > 100$), and passive eavesdropping lacking traffic anomalies. In addition, partition elimination is a direct consequence of the articulation-aware constraint barring cut-vertex quarantine, rather than detection accuracy alone.

\\noindent\\textit{Conclusion:} We presented a closed-loop digital twin unifying topology-aware GAT detection, Bayesian trust estimation, lookahead simulation, and Wald SPRT verification. Across 600 runs, enforcing articulation-aware constraints prevented network partitioning under all evaluated attack scenarios ($0.00\\%$ observed partition rate vs. $72.50\\%$ in static IDS) by replacing cut-vertex quarantine with dynamic bypass detours and rate clamping, achieving a 24.9\\% resilience gain within a 500-ms edge deadline. Artifacts: \\url{https://github.com/anonymous-dt-iot/self-healing-dt}.

\\bibliographystyle{IEEEtran}
\\begin{thebibliography}{19}
\\setlength{\\itemsep}{0.5pt}
\\setlength{\\parskip}{0pt}
\\footnotesize
\\bibitem{yigit2024ai} Y. Yigit, K. N. Choobdar, B. Yamansavascilar, B. Canberk, and Z. Han, ``AI-enhanced digital twin framework for cyber-resilient 6G Internet of Vehicles networks,'' \\textit{IEEE Internet of Things J.}, vol. 11, no. 22, pp. 36168--36181, Nov. 2024.
\\bibitem{mani2023machine} G. Mani, B. Bhargava, B. Shivakumar, and J. Kobes, ``Machine learning based resilience testing of an address randomization cyber defense,'' \\textit{IEEE Trans. Dependable Secure Comput.}, vol. 20, no. 6, pp. 4853--4867, Nov.--Dec. 2023.
\\bibitem{ge2024gazeta} Y. Ge and Q. Zhu, ``GAZETA: Game-theoretic zero-trust authentication for defense against lateral movement in 5G IoT networks,'' \\textit{IEEE Trans. Inf. Forensics Security}, vol. 19, pp. 540--554, 2024.
\\bibitem{liu2024region} X. Liu, X. Zeng, J. Ren, S. Yin, and H. Zhou, ``Region-different network reconfiguration in disjoint wireless sensor networks for smart agriculture monitoring,'' \\textit{ACM Trans. Sensor Netw.}, vol. 20, no. 2, pp. 1--20, 2024.
\\bibitem{debenedictis2023digital} A. De Benedictis, A. Somma, and A. Tedesco, ``Digital twins for anomaly detection in the industrial Internet of Things: Conceptual architecture and proof-of-concept,'' \\textit{IEEE Trans. Ind. Informat.}, vol. 19, no. 12, pp. 11553--11563, Dec. 2023.
\\bibitem{guan2023resilient} M. Guan and Y. Chen, ``Resilient distributed consensus in adversarial wireless sensor networks,'' \\textit{IEEE Trans. Mobile Comput.}, vol. 22, no. 8, pp. 4812--4825, Aug. 2023.
\\bibitem{khan2022digital} L. U. Khan, W. Saad, D. Niyato, Z. Han, and C. S. Hong, ``Digital twin of wireless systems: Overview, taxonomy, challenges, and opportunities,'' \\textit{IEEE Commun. Surveys Tuts.}, vol. 24, no. 4, pp. 2230--2254, 4th Quart. 2022.
\\bibitem{upadhyaya2021multihypothesis} B. Upadhyaya, S. Sun, and B. Sikdar, ``Multihypothesis sequential testing for illegitimate access and collision-based attack detection in wireless IoT networks,'' \\textit{IEEE Internet of Things J.}, vol. 8, no. 14, pp. 11705--11716, Jul. 2021.
\\bibitem{kouicem2022decentralized} D. E. Kouicem, Y. Imine, A. Bouabdallah, and H. Lakhlef, ``Decentralized blockchain-based trust management protocol for the Internet of Things,'' \\textit{IEEE Trans. Dependable Secure Comput.}, vol. 19, no. 2, pp. 1292--1306, Mar.--Apr. 2022.
\\bibitem{wu2023heterogeneous} J. Wu, H. Dai, Y. Wang, K. Ye, and C. Xu, ``Heterogeneous domain adaptation for IoT intrusion detection: A geometric graph alignment approach,'' \\textit{IEEE Internet of Things J.}, vol. 10, no. 12, pp. 10764--10777, Jun. 2023.
\\bibitem{jia2023virtual} P. Jia and X. Wang, ``A new virtual network topology-based digital twin for spatial-temporal load-balanced user association in 6G HetNets,'' \\textit{IEEE J. Sel. Areas Commun.}, vol. 41, no. 10, pp. 3080--3094, Oct. 2023.
\\bibitem{yang2024enabling} L. Yang, M. E. Rajab, A. Shami, and S. Muhaidat, ``Enabling AutoML for zero-touch network security: Use-case driven analysis,'' \\textit{IEEE Trans. Netw. Service Manag.}, vol. 21, no. 3, pp. 3555--3582, Jun. 2024.
\\bibitem{sood2023intrusion} K. Sood, S. Garg, N. Kumar, and M. Guizani, ``Intrusion detection scheme with dimensionality reduction in next generation networks,'' \\textit{IEEE Trans. Inf. Forensics Security}, vol. 18, pp. 965--979, 2023.
\\bibitem{liu2022selfhealing} J. Liu, S. Guo, L. Chen, and K. Wang, ``A self-healing routing strategy based on ant colony optimization for vehicular ad hoc networks,'' \\textit{IEEE Internet of Things J.}, vol. 9, no. 22, pp. 22695--22709, Nov. 2022.
\\bibitem{li2021deepfed} B. Li, Y. Lu, W. Wei, and J. Huang, ``DeepFed: Federated deep learning for intrusion detection in industrial cyber-physical systems,'' \\textit{IEEE Trans. Ind. Informat.}, vol. 17, no. 8, pp. 5615--5624, Aug. 2021.
\\bibitem{heinzelman2000energy} W. R. Heinzelman, A. Chandrakasan, and H. Balakrishnan, ``Energy-efficient communication protocol for wireless microsensor networks,'' in \\textit{Proc. 33rd HICSS}, pp. 1--10, 2000.
\\bibitem{velickovic2018graph} P. Veli\\v{c}kovi\\'c \\textit{et al.}, ``Graph attention networks,'' in \\textit{Proc. Int. Conf. Learn. Represent. (ICLR)}, pp. 1--12, 2018.
\\bibitem{lo2022egraphsage} W. W. Lo \\textit{et al.}, ``E-GraphSAGE: A graph neural network based intrusion detection system for IoT,'' in \\textit{IEEE/IFIP NOMS}, pp. 1--9, 2022.
\\bibitem{wang2021one} X. Wang, B. Jin, Y. Du, P. Cui, Y. Tan, and Y. Yang, ``One-class graph neural networks for anomaly detection in attributed networks,'' \\textit{Neural Comput. Applic.}, vol. 33, no. 18, pp. 12073--12085, 2021.
\\end{thebibliography}

\\end{document}
"""

full_content = lines_1_to_120 + "\n" + lines_121_to_250 + "\n" + lines_251_to_411

with open("manuscript_6pages_baseline.tex", "w", encoding="utf-8") as f:
    f.write(full_content.strip() + "\n")

print("Saved manuscript_6pages_baseline.tex, len:", len(full_content))
