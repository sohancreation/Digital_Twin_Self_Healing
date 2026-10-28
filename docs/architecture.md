# System Architecture & Roadmap

This document outlines the modular architecture of the **Digital Twin-Based Cyber Attack Detection and Self-Healing Framework for Resource-Constrained IoT Networks**.

---

## 1. Modular Architecture Progression

```
[IoT Physical / Simulated Layer] (Phase 1 - COMPLETED)
         │
         │  Standardized Telemetry Stream (TelemetryRecord)
         ▼
[Controlled Cyberattack Framework] (Phase 3 - COMPLETED)
         │
         ├── DoS / Packet Flooding Engine (backend/attacks/dos.py)
         ├── Compromised Node Selective Drop Engine (backend/attacks/compromised_node.py)
         ├── Node Failure / Outage Engine (backend/attacks/node_failure.py)
         ├── Deterministic Attack Scheduler (backend/attacks/scheduler.py)
         └── Ground-Truth Annotation Recorder (backend/attacks/ground_truth.py)
         │
         │  Annotated Telemetry + Ground Truth Labels
         ▼
[Digital Twin State Synchronizer & Shadow Model] (Phase 2 - COMPLETED)
         │
         ├── Current Node Shadow States (TwinNodeState)
         ├── Bounded Temporal History (HistoryManager)
         ├── Topology Shadow & Link Conditions (NetworkTopologyModel)
         └── Macroscopic Health Monitoring (NetworkHealthSummary)
         │
         ▼
[Data Engineering & Feature Extraction Pipeline] (Phase 4 - COMPLETED)
         │
         ├── Multi-Scale Rolling Windows (W = 5s, 15s, 30s)
         ├── First-Order Rate-of-Change Derivatives
         ├── Domain Interaction & Congestion Ratios
         ├── Spatial Network Discrepancy Indicators
         └── Leakage-Free Chronological & Cross-Seed Partitions
         │
         ▼
[Machine Learning Detection Engine] (Phase 5 - NEXT)
         │
         ├── Interpretable Classifiers (Logistic Regression, Random Forest, XGBoost)
         ├── Multi-Metric Evaluation (F1, ROC-AUC, FPR, FNR, Inference Latency)
         └── Export for Phase 6 Trust Scoring
         │
         ├── [Phase 6] Dynamic Risk & Trust Engine
         ├── [Phase 7] Recovery Strategy Candidate Generator
         ├── [Phase 8] Digital Twin Recovery Simulation (In Silico Pre-Evaluation)
         └── [Phase 9] Autonomous Self-Healing & Closed-Loop Actuation
```

---

## 2. Directory Structure

```text
E:\G_Publication/
├── backend/
│   ├── simulation/             # Phase 1: IoT Network Simulator
│   │   ├── __init__.py
│   │   ├── config.py           # Simulation Pydantic models
│   │   ├── telemetry.py        # TelemetryRecord schema
│   │   ├── node.py             # IoTNode dynamic models
│   │   ├── topology.py         # NetworkX topology layouts
│   │   └── simulator.py        # Discrete-time simulator
│   │
│   ├── digital_twin/           # Phase 2: Digital Twin Shadow System
│   │   ├── __init__.py
│   │   ├── models.py           # TwinNodeState, LinkState, NetworkTwinState, SyncMetadata
│   │   ├── history.py          # Time-windowed historical state buffers
│   │   ├── topology_model.py   # Topology shadow and directional link conditions
│   │   ├── health.py           # Descriptive network health assessment
│   │   ├── synchronizer.py     # Telemetry ingestion and latency measurement
│   │   └── twin.py             # Core Digital Twin engine & query API
│   │
│   ├── attacks/                # Phase 3: Controlled Cyberattack Simulation
│   │   ├── __init__.py
│   │   ├── models.py           # AttackConfig, AttackGroundTruth
│   │   ├── base.py             # BaseAttack abstract lifecycle interface
│   │   ├── dos.py              # DoS / Flooding attack model
│   │   ├── compromised_node.py # Compromised node selective packet dropping
│   │   ├── node_failure.py     # Controlled node failure & recovery model
│   │   ├── scheduler.py        # Deterministic attack schedule coordinator
│   │   ├── ground_truth.py     # Ground-truth label recorder & CSV exporter
│   │   └── injector.py         # Simulation attack coordinator
│   │
│   └── data_engineering/      # Phase 4: Feature Engineering & Dataset Preparation
│       ├── __init__.py
│       ├── extractor.py        # Multi-scale rolling windows, deltas & spatial features
│       ├── preprocessor.py     # Scaler fit/transform and metadata persistence
│       ├── dataset.py          # Target encoding, chronological partitioning & balance
│       └── pipeline.py         # Unified end-to-end processing pipeline
│
├── configs/
│   └── simulation.yaml         # Parameterized YAML configuration
│
├── docs/
│   ├── architecture.md         # System architecture & roadmap
│   ├── feature_engineering.md  # Feature formulations, windows & leakage safeguards
│   ├── attacks.md              # Cyberattack models, equations & scheduler semantics
│   ├── digital_twin.md         # Digital Twin design, models & sync semantics
│   ├── assumptions.md          # Physical, computational & channel assumptions
│   ├── telemetry_schema.md     # Telemetry field descriptions and units
│   └── RESEARCH_MASTER_PLAN.md # 13-phase comprehensive research master plan
│
├── models/
│   └── datasets/               # Preprocessed ML datasets & metadata
│       ├── features_phase4_full.csv
│       ├── train_set.csv
│       ├── val_set.csv
│       ├── test_set.csv
│       ├── test_cross_seed.csv
│       └── feature_metadata.json
│
├── plots/                      # Publication-quality validation figures (Phases 1-4)
├── results/                    # Exported raw telemetry and ground-truth datasets
├── scripts/
│   ├── run_simulation.py       # Baseline simulator runner
│   ├── generate_plots.py       # Phase 1 validation plotting
│   ├── run_phase2_experiment.py# Phase 2 sync experiment & plotting
│   ├── run_phase3_experiments.py # Phase 3 multi-attack experiments & plotting
│   └── run_phase4_feature_pipeline.py # Phase 4 feature extraction & dataset generation
│
├── tests/
│   ├── test_node.py            # Node dynamics & energy tests
│   ├── test_topology.py        # Topology generation & symmetry tests
│   ├── test_telemetry.py       # TelemetryRecord validation tests
│   ├── test_simulator.py       # Simulator progression & reproducibility tests
│   ├── test_digital_twin.py    # DT models, history, topology shadow & health tests
│   ├── test_phase2_integration.py # Phase 2 Simulator -> DT integration tests
│   ├── test_attacks.py         # Attack models, scheduler, boundaries & non-interference tests
│   ├── test_phase3_integration.py # Phase 3 Simulator -> Injector -> Ground Truth -> DT tests
│   └── test_feature_engineering.py # Phase 4 feature extraction, causality & split tests
│
├── DEVELOPMENT_STATUS.md       # Formal phase tracking, test reports, and phase gates
├── requirements.txt            # Dependency specification
└── README.md                   # Setup and execution guide
```
