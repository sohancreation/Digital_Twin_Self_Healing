"""
Launcher script for Phase 10: Real-Time Research Monitoring Dashboard.
Starts the high-performance FastAPI backend with WebSocket telemetry streaming
and hosts the interactive dark glassmorphism research mission control UI.
"""

import argparse
import sys
from pathlib import Path

# Ensure root directory is on Python path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import uvicorn


def print_banner(host: str, port: int):
    url = f"http://{host}:{port}"
    banner = f"""
========================================================================================
       IoTDTR - PHASE 10: REAL-TIME RESEARCH MONITORING MISSION CONTROL
========================================================================================
  Autonomous Cyber-Physical Digital Twin Telemetry & Self-Healing Command Center
  --------------------------------------------------------------------------------------
  * Dashboard URL:       {url}
  * WebSocket Stream:    ws://{host}:{port}/ws/telemetry
  * REST API Specs:      {url}/docs
  * Operational Target:  IEEE/ACM Transactions Multi-Phase Demonstration

  Integrated Capabilities:
    [+] Live SVG Topology Graph with Dynamic Operational States & Cut-Vertex Badging
    [+] Multi-Channel Sliding Chart.js Telemetry (PDR, Loss, Latency, Throughput, QoS)
    [+] Physical vs Virtual Twin Synchronization Fidelity & Clock Drift Tracking
    [+] Interactive Attack Injection (DoS, Selective Drop, Node Failure, On-Off)
    [+] ML Intrusion Inference & Bayesian Trust Decomposition Matrix
    [+] Closed-Loop Mitigation Actuation with Pareto TOPSIS & Wald SPRT Verifier
    [+] Instant Automated Safety Rollback to Pre-Actuation Baseline (S_pre)

  Press Ctrl+C to terminate the dashboard server gracefully.
========================================================================================
"""
    print(banner)


def main():
    parser = argparse.ArgumentParser(description="Run Phase 10 Research Monitoring Dashboard")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host binding address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port binding (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable uvicorn hot reloading for development")

    args = parser.parse_args()
    print_banner(args.host, args.port)

    uvicorn.run(
        "backend.dashboard.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
