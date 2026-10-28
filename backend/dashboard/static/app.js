/**
 * IoTDTR - Phase 10: Real-Time Research Monitoring Dashboard
 * Frontend Application Engine: WebSocket Streaming, Interactive SVG Topology,
 * Sliding Chart.js Visualizations, and Closed-Loop Control Handlers.
 */

(function () {
  'use strict';

  // State Management
  let isRunning = false;
  let selectedNodeId = 2;
  let lastTick = -1;
  let ws = null;
  let charts = {};
  const maxHistoryPoints = 30;

  // DOM Elements Cache
  const el = {
    lblTick: document.getElementById('lbl-tick'),
    lblTime: document.getElementById('lbl-time'),
    btnPlayPause: document.getElementById('btn-play-pause'),
    iconPlay: document.getElementById('icon-play'),
    textPlay: document.getElementById('text-play'),
    btnStep: document.getElementById('btn-step'),
    btnReset: document.getElementById('btn-reset'),
    btnRollback: document.getElementById('btn-rollback'),
    selSpeed: document.getElementById('sel-speed'),
    
    // KPIs
    kpiPdr: document.getElementById('kpi-pdr'),
    kpiLoss: document.getElementById('kpi-loss'),
    kpiLatency: document.getElementById('kpi-latency'),
    kpiThroughput: document.getElementById('kpi-throughput'),
    kpiBattery: document.getElementById('kpi-battery'),
    kpiResilience: document.getElementById('kpi-resilience'),

    // Topology
    svgEdgesLayer: document.getElementById('svg-edges-layer'),
    svgNodesLayer: document.getElementById('svg-nodes-layer'),
    topoStatusDot: document.getElementById('topology-status-dot'),
    lblTopoNodes: document.getElementById('lbl-topo-nodes'),

    // Node Inspector
    inspTitle: document.getElementById('insp-title'),
    inspBadge: document.getElementById('insp-badge'),
    inspTrust: document.getElementById('insp-trust'),
    inspDirect: document.getElementById('insp-direct'),
    inspLoss: document.getElementById('insp-loss'),
    inspLatency: document.getElementById('insp-latency'),
    inspRate: document.getElementById('insp-rate'),
    inspBattery: document.getElementById('insp-battery'),
    inspQueue: document.getElementById('insp-queue'),
    inspCut: document.getElementById('insp-cut'),

    // Fidelity
    lblFidelityScore: document.getElementById('lbl-fidelity-score'),
    fidClock: document.getElementById('fid-clock'),
    fidDiscrepancy: document.getElementById('fid-discrepancy'),
    fidLossDelta: document.getElementById('fid-loss-delta'),
    fidLatencyDelta: document.getElementById('fid-latency-delta'),

    // ML Threat
    mlBadge: document.getElementById('ml-badge'),
    mlConfidence: document.getElementById('ml-confidence'),
    mlLatency: document.getElementById('ml-latency'),
    probNormal: document.getElementById('prob-normal'),
    probDos: document.getElementById('prob-dos'),
    probDrop: document.getElementById('prob-drop'),
    probFailure: document.getElementById('prob-failure'),

    // GNN Defense Panel (BridgeAwareGAT & Thm. 4)
    gnnBadge: document.getElementById('gnn-badge'),
    gnnTargetThreat: document.getElementById('gnn-target-threat'),
    gnnFusedTrust: document.getElementById('gnn-fused-trust'),
    gnnPredTrust: document.getElementById('gnn-pred-trust'),
    gnnLatency: document.getElementById('gnn-latency'),
    gnnDetourStatus: document.getElementById('gnn-detour-status'),
    gnnAttentionGrid: document.getElementById('gnn-attention-grid'),
    inspFusedTrust: document.getElementById('insp-fused-trust'),
    inspGnnThreat: document.getElementById('insp-gnn-threat'),

    // Resilience & SPRT
    kpiAuditTier: document.getElementById('kpi-audit-tier'),
    kpiSprtVal: document.getElementById('kpi-sprt-val'),
    kpiSprtDec: document.getElementById('kpi-sprt-dec'),
    kpiFlappingIdx: document.getElementById('kpi-flapping-idx'),
    kpiDampingStatus: document.getElementById('kpi-damping-status'),

    // Attack Form
    selAttackType: document.getElementById('sel-attack-type'),
    selAttackTarget: document.getElementById('sel-attack-target'),
    inpAttackDuration: document.getElementById('inp-attack-duration'),
    inpAttackIntensity: document.getElementById('inp-attack-intensity'),
    inpDropProb: document.getElementById('inp-drop-prob'),
    btnInjectAttack: document.getElementById('btn-inject-attack'),
    btnStopAttack: document.getElementById('btn-stop-attack'),

    // Self-Healing
    selWeightProfile: document.getElementById('sel-weight-profile'),
    btnTriggerHealing: document.getElementById('btn-trigger-healing'),
    auditTerminal: document.getElementById('audit-terminal'),

    // Footer Status
    wsIndicator: document.getElementById('ws-indicator'),
    wsStatusText: document.getElementById('ws-status-text'),
  };

  // --- 1. Real-Time Sliding Charts Initialization ---
  function initCharts() {
    const commonOptions = {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 0 },
      plugins: {
        legend: { labels: { color: '#94a3b8', font: { size: 10, family: 'Inter' } } }
      },
      scales: {
        x: {
          grid: { color: 'rgba(255, 255, 255, 0.05)' },
          ticks: { color: '#64748b', font: { size: 9, family: 'JetBrains Mono' } }
        },
        y: {
          grid: { color: 'rgba(255, 255, 255, 0.05)' },
          ticks: { color: '#94a3b8', font: { size: 9, family: 'JetBrains Mono' } }
        }
      }
    };

    // Chart 1: PDR & Loss
    charts.pdrLoss = new Chart(document.getElementById('chart-pdr-loss').getContext('2d'), {
      type: 'line',
      data: {
        labels: [],
        datasets: [
          {
            label: 'PDR (%)',
            data: [],
            borderColor: '#10b981',
            backgroundColor: 'rgba(16, 185, 129, 0.1)',
            tension: 0.25,
            pointRadius: 2,
            yAxisID: 'y'
          },
          {
            label: 'Loss (%)',
            data: [],
            borderColor: '#ef4444',
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            tension: 0.25,
            pointRadius: 2,
            yAxisID: 'y'
          }
        ]
      },
      options: {
        ...commonOptions,
        scales: {
          ...commonOptions.scales,
          y: { ...commonOptions.scales.y, min: 0, max: 100 }
        }
      }
    });

    // Chart 2: Latency
    charts.latency = new Chart(document.getElementById('chart-latency').getContext('2d'), {
      type: 'line',
      data: {
        labels: [],
        datasets: [{
          label: 'Latency (ms)',
          data: [],
          borderColor: '#0ea5e9',
          backgroundColor: 'rgba(14, 165, 233, 0.1)',
          tension: 0.25,
          pointRadius: 2,
          fill: true
        }]
      },
      options: {
        ...commonOptions,
        scales: {
          ...commonOptions.scales,
          y: { ...commonOptions.scales.y, min: 0 }
        }
      }
    });

    // Chart 3: Throughput
    charts.throughput = new Chart(document.getElementById('chart-throughput').getContext('2d'), {
      type: 'line',
      data: {
        labels: [],
        datasets: [{
          label: 'Throughput (pkts/s)',
          data: [],
          borderColor: '#6366f1',
          backgroundColor: 'rgba(99, 102, 241, 0.1)',
          tension: 0.25,
          pointRadius: 2,
          fill: true
        }]
      },
      options: commonOptions
    });

    // Chart 4: QoS & Battery
    charts.qosBattery = new Chart(document.getElementById('chart-qos-battery').getContext('2d'), {
      type: 'line',
      data: {
        labels: [],
        datasets: [
          {
            label: 'QoS Q(t)',
            data: [],
            borderColor: '#a855f7',
            tension: 0.25,
            pointRadius: 2,
            yAxisID: 'yQos'
          },
          {
            label: 'Battery (%)',
            data: [],
            borderColor: '#f59e0b',
            tension: 0.25,
            pointRadius: 2,
            yAxisID: 'yBattery'
          }
        ]
      },
      options: {
        ...commonOptions,
        scales: {
          ...commonOptions.scales,
          yQos: {
            type: 'linear',
            position: 'left',
            min: 0,
            max: 1.0,
            grid: { color: 'rgba(255, 255, 255, 0.05)' },
            ticks: { color: '#a855f7' }
          },
          yBattery: {
            type: 'linear',
            position: 'right',
            min: 0,
            max: 100,
            grid: { drawOnChartArea: false },
            ticks: { color: '#f59e0b' }
          }
        }
      }
    });
  }

  function appendChartData(frame) {
    const timeLabel = `${frame.timestamp.toFixed(1)}s`;

    const addPoint = (chart, values) => {
      chart.data.labels.push(timeLabel);
      if (chart.data.labels.length > maxHistoryPoints) {
        chart.data.labels.shift();
      }
      chart.data.datasets.forEach((ds, idx) => {
        ds.data.push(values[idx]);
        if (ds.data.length > maxHistoryPoints) {
          ds.data.shift();
        }
      });
      chart.update('none');
    };

    addPoint(charts.pdrLoss, [frame.network_pdr * 100, frame.network_loss * 100]);
    addPoint(charts.latency, [frame.network_latency_ms]);
    addPoint(charts.throughput, [frame.network_throughput_pkts_s]);
    addPoint(charts.qosBattery, [frame.instantaneous_qos, frame.network_energy_pct]);
  }

  // --- 2. Interactive SVG Network Topology Rendering ---
  function renderTopology(topology) {
    if (!topology || !topology.nodes) return;

    // Node lookup map
    const nodeMap = {};
    topology.nodes.forEach(n => { nodeMap[n.node_id] = n; });

    // Render Edges
    let edgesHtml = '';
    topology.edges.forEach(edge => {
      const u = nodeMap[edge.source];
      const v = nodeMap[edge.target];
      if (!u || !v) return;

      let linkClass = 'svg-link active';
      if (edge.is_bridged) linkClass = 'svg-link bridged';
      if (edge.status === 'SEVERED') linkClass = 'svg-link severed';

      edgesHtml += `<line class="${linkClass}" x1="${u.x}" y1="${u.y}" x2="${v.x}" y2="${v.y}" />`;
    });
    el.svgEdgesLayer.innerHTML = edgesHtml;

    // Render Nodes
    let nodesHtml = '';
    topology.nodes.forEach(node => {
      let fillColor = '#10b981'; // NOMINAL
      let glowFilter = 'url(#glow-cyan)';
      if (node.operational_state === 'ATTACKED') {
        fillColor = '#ef4444';
        glowFilter = 'url(#glow-crimson)';
      } else if (node.operational_state === 'DEGRADED') {
        fillColor = '#f59e0b';
      } else if (node.operational_state === 'QUARANTINED') {
        fillColor = '#a855f7';
      } else if (node.operational_state === 'REBOOTING') {
        fillColor = '#0ea5e9';
      } else if (node.operational_state === 'OFFLINE') {
        fillColor = '#475569';
      }

      const isSelected = (node.node_id === selectedNodeId);
      const strokeWidth = isSelected ? '3.5' : '1.5';
      const strokeColor = isSelected ? '#ffffff' : 'rgba(255,255,255,0.4)';

      // Trust halo radius
      const haloRadius = 24;
      const strokeDash = `${(node.trust_score * 150).toFixed(1)}, 150`;

      // Cut vertex badge
      const cutBadge = node.is_cut_vertex 
        ? `<polygon points="${node.x},${node.y - 32} ${node.x+4},${node.y - 24} ${node.x-4},${node.y - 24}" fill="#f59e0b" />`
        : '';

      nodesHtml += `
        <g class="svg-node" onclick="window.selectDashboardNode(${node.node_id})">
          <!-- Trust Halo Ring -->
          <circle cx="${node.x}" cy="${node.y}" r="${haloRadius}" fill="none" stroke="${fillColor}" stroke-width="2" stroke-dasharray="${strokeDash}" opacity="0.6" />
          <!-- Main Node Circle -->
          <circle cx="${node.x}" cy="${node.y}" r="17" fill="${fillColor}" stroke="${strokeColor}" stroke-width="${strokeWidth}" filter="${glowFilter}" />
          <!-- Label -->
          <text x="${node.x}" y="${node.y + 4.5}" text-anchor="middle" fill="#ffffff" font-size="11" font-weight="700" font-family="'JetBrains Mono', monospace">N${node.node_id}</text>
          ${cutBadge}
        </g>
      `;
    });
    el.svgNodesLayer.innerHTML = nodesHtml;

    el.lblTopoNodes.textContent = `${topology.nodes.length} Nodes | ${topology.edges.length} Links`;
    if (topology.is_partitioned) {
      el.lblTopoNodes.textContent += ' [PARTITIONED]';
      el.lblTopoNodes.style.color = '#ef4444';
    } else {
      el.lblTopoNodes.style.color = 'var(--text-dim)';
    }
  }

  // --- 3. Telemetry Frame Ingestion & UI Binding ---
  function handleTelemetryFrame(frame) {
    if (!frame || frame.tick === lastTick) return;
    lastTick = frame.tick;

    // Header Clock
    el.lblTick.textContent = `Tick: ${frame.tick}`;
    el.lblTime.textContent = `${frame.timestamp.toFixed(1)}s`;

    // Top KPIs
    el.kpiPdr.textContent = `${(frame.network_pdr * 100).toFixed(1)}%`;
    el.kpiLoss.textContent = `${(frame.network_loss * 100).toFixed(1)}%`;
    el.kpiLatency.textContent = `${frame.network_latency_ms.toFixed(1)} ms`;
    el.kpiThroughput.textContent = `${frame.network_throughput_pkts_s.toFixed(1)} pkts/s`;
    el.kpiBattery.textContent = `${frame.network_energy_pct.toFixed(1)}%`;
    el.kpiResilience.textContent = frame.macroscopic_resilience_r.toFixed(3);

    // Active Attack Status Indicator
    const hasAttacks = (frame.active_attacks && frame.active_attacks.length > 0);
    if (hasAttacks) {
      el.topoStatusDot.className = 'status-indicator attack';
    } else {
      el.topoStatusDot.className = 'status-indicator';
    }

    // Render Topology
    renderTopology(frame.topology);

    // Update Node Inspector for Selected Node
    updateNodeInspector(frame.topology);

    // Append to sliding Chart.js series
    appendChartData(frame);

    // Digital Twin Fidelity
    if (frame.fidelity) {
      el.lblFidelityScore.textContent = `${(frame.fidelity.shadow_fidelity_score * 100).toFixed(1)}%`;
      el.fidClock.textContent = `${frame.fidelity.clock_drift_ms.toFixed(2)} ms`;
      el.fidDiscrepancy.textContent = frame.fidelity.mean_state_discrepancy.toFixed(4);
      el.fidLossDelta.textContent = frame.fidelity.loss_delta.toFixed(4);
      el.fidLatencyDelta.textContent = `${frame.fidelity.latency_delta_ms.toFixed(2)} ms`;
    }

    // ML Threat Inference
    if (frame.ml_prediction) {
      const ml = frame.ml_prediction;
      el.mlBadge.textContent = ml.predicted_label.toUpperCase();
      if (ml.is_anomaly) {
        el.mlBadge.style.background = 'rgba(239, 68, 68, 0.2)';
        el.mlBadge.style.color = '#ef4444';
      } else {
        el.mlBadge.style.background = 'rgba(16, 185, 129, 0.2)';
        el.mlBadge.style.color = '#10b981';
      }
      el.mlConfidence.textContent = `${(ml.confidence * 100).toFixed(1)}%`;
      el.mlLatency.textContent = `${ml.inference_latency_ms.toFixed(2)} ms`;

      const probs = ml.probabilities || {};
      el.probNormal.style.width = `${((probs.normal || 0) * 100).toFixed(1)}%`;
      el.probDos.style.width = `${((probs.dos || 0) * 100).toFixed(1)}%`;
      el.probDrop.style.width = `${((probs.compromised || 0) * 100).toFixed(1)}%`;
      el.probFailure.style.width = `${((probs.failure || 0) * 100).toFixed(1)}%`;
    }

    // GNN Cyber-Defense Panel Binding (BridgeAwareGAT & Thm. 4)
    if (frame.gnn) {
      const gnn = frame.gnn;
      const targetStr = String(selectedNodeId);
      const threat = (gnn.predicted_classes && gnn.predicted_classes[targetStr]) || 'Normal';
      if (el.gnnTargetThreat) {
        el.gnnTargetThreat.textContent = threat;
        el.gnnTargetThreat.style.color = (threat === 'Normal') ? '#10b981' : '#ef4444';
      }

      if (el.gnnFusedTrust && gnn.t_fused && gnn.t_fused[targetStr] !== undefined) {
        el.gnnFusedTrust.textContent = Number(gnn.t_fused[targetStr]).toFixed(3);
      }
      if (el.gnnPredTrust && gnn.t_gnn && gnn.t_gnn[targetStr] !== undefined) {
        el.gnnPredTrust.textContent = Number(gnn.t_gnn[targetStr]).toFixed(3);
      }
      if (el.gnnLatency && gnn.inference_latency_ms !== undefined) {
        el.gnnLatency.textContent = `${Number(gnn.inference_latency_ms).toFixed(2)} ms`;
      }
      if (el.gnnDetourStatus) {
        if (gnn.detour_active) {
          el.gnnDetourStatus.textContent = 'ACTIVE (BYPASS REROUTE)';
          el.gnnDetourStatus.style.color = '#38bdf8';
        } else {
          el.gnnDetourStatus.textContent = 'STANDBY';
          el.gnnDetourStatus.style.color = '#10b981';
        }
      }

      // Render 6x6 attention grid
      if (gnn.attention_matrix && gnn.attention_matrix.length === 6 && el.gnnAttentionGrid) {
        let gridHtml = '';
        for (let r = 0; r < 6; r++) {
          for (let c = 0; c < 6; c++) {
            const val = gnn.attention_matrix[r][c];
            const isBridge = (r === 2 && c === 3) || (r === 3 && c === 2) || (r === 3 && c === 4) || (r === 4 && c === 3);
            const bg = isBridge ? 'rgba(245, 158, 11, 0.25)' : (val > 0.1 ? 'rgba(56, 189, 248, 0.2)' : 'rgba(255, 255, 255, 0.03)');
            const textCol = isBridge ? '#f59e0b' : (val > 0.1 ? '#38bdf8' : '#64748b');
            gridHtml += `<div style="background: ${bg}; color: ${textCol}; padding: 2px; border-radius: 2px;">${val.toFixed(2)}</div>`;
          }
        }
        el.gnnAttentionGrid.innerHTML = gridHtml;
      }
    }

    // Closed-Loop Mitigation & Audit State
    if (frame.recent_audit) {
      const aud = frame.recent_audit;
      el.kpiAuditTier.textContent = aud.escalation_tier.replace(/_/g, ' ');
      el.kpiSprtVal.textContent = (aud.sprt_log_likelihood !== null && aud.sprt_log_likelihood !== undefined)
        ? aud.sprt_log_likelihood.toFixed(2)
        : '0.00';
      el.kpiSprtDec.textContent = aud.sprt_decision || 'CONTINUE';
      el.kpiFlappingIdx.textContent = (aud.flapping_index || 0).toFixed(2);
      el.kpiDampingStatus.textContent = aud.is_flapping_held_down ? 'HELD-DOWN (SUPPRESSED)' : 'PASSIVE';
      el.kpiDampingStatus.style.color = aud.is_flapping_held_down ? '#ef4444' : '#10b981';

      // Update Audit Terminal
      appendAuditLog(`[${frame.timestamp.toFixed(1)}s] ${aud.action_type || 'ACTION'}: ${aud.explanation_summary || ''}`);
    }
  }

  function updateNodeInspector(topology) {
    if (!topology || !topology.nodes) return;
    const node = topology.nodes.find(n => n.node_id === selectedNodeId) || topology.nodes[0];
    if (!node) return;

    el.inspTitle.textContent = `Node #${node.node_id} Telemetry`;
    el.inspBadge.textContent = node.operational_state;
    el.inspTrust.textContent = node.trust_score.toFixed(3);
    if (el.inspFusedTrust) el.inspFusedTrust.textContent = (node.t_fused !== undefined ? Number(node.t_fused).toFixed(3) : node.trust_score.toFixed(3));
    if (el.inspGnnThreat) el.inspGnnThreat.textContent = node.gnn_threat || 'Normal';
    el.inspLoss.textContent = (node.packet_loss * 100).toFixed(1) + '%';
    el.inspLatency.textContent = `${node.latency_ms.toFixed(1)} ms`;
    el.inspRate.textContent = `${node.packet_rate.toFixed(1)} pkts/s`;
    el.inspBattery.textContent = `${node.energy_pct.toFixed(1)}%`;
    el.inspQueue.textContent = node.queue_length;
    el.inspCut.textContent = node.is_cut_vertex ? 'YES (Articulation Point)' : 'No';
    el.inspCut.style.color = node.is_cut_vertex ? '#f59e0b' : '#94a3b8';

    // Fetch detailed Bayesian trust decomposition from REST endpoint
    fetch(`/api/node/${node.node_id}/trust`)
      .then(res => res.json())
      .then(data => {
        el.inspDirect.textContent = data.direct_trust.toFixed(3);
      })
      .catch(() => {});
  }

  window.selectDashboardNode = function (nodeId) {
    selectedNodeId = nodeId;
    // Re-render topology to show updated selection border
    fetch('/api/state')
      .then(res => res.json())
      .then(frame => {
        renderTopology(frame.topology);
        updateNodeInspector(frame.topology);
      })
      .catch(console.error);
  };

  function appendAuditLog(text, isDanger = false) {
    const entry = document.createElement('div');
    entry.className = 'audit-entry';
    if (isDanger) entry.style.color = '#ef4444';
    entry.textContent = text;
    el.auditTerminal.appendChild(entry);
    el.auditTerminal.scrollTop = el.auditTerminal.scrollHeight;
  }

  // --- 4. WebSocket Streaming Engine ---
  function connectWebSocket() {
    const loc = window.location;
    const proto = (loc.protocol === 'https:') ? 'wss:' : 'ws:';
    const wsUrl = `${proto}//${loc.host}/ws/telemetry`;

    el.wsStatusText.textContent = 'Telemetry Stream: Connecting...';
    el.wsIndicator.style.background = '#f59e0b';

    ws = new WebSocket(wsUrl);

    ws.onopen = function () {
      el.wsStatusText.textContent = 'Telemetry Stream: Live (WebSocket)';
      el.wsIndicator.style.background = '#10b981';
      appendAuditLog('[WS_CONNECT] Real-time binary telemetry stream connected successfully.');
    };

    ws.onmessage = function (event) {
      try {
        const frame = JSON.parse(event.data);
        handleTelemetryFrame(frame);
      } catch (err) {
        console.error('Error parsing telemetry frame:', err);
      }
    };

    ws.onclose = function () {
      el.wsStatusText.textContent = 'Telemetry Stream: Disconnected (Reconnecting in 2s...)';
      el.wsIndicator.style.background = '#ef4444';
      setTimeout(connectWebSocket, 2000);
    };

    ws.onerror = function () {
      ws.close();
    };
  }

  // --- 5. Interactive Simulation Controls ---
  function bindEventHandlers() {
    // Play / Pause
    el.btnPlayPause.addEventListener('click', () => {
      const speed = parseFloat(el.selSpeed.value);
      if (!isRunning) {
        fetch(`/api/play?speed=${speed}`, { method: 'POST' })
          .then(res => res.json())
          .then(() => {
            isRunning = true;
            el.iconPlay.innerHTML = '&#10074;&#10074;';
            el.textPlay.textContent = 'Pause';
            appendAuditLog('[SIM_RUN] Simulation continuous streaming started.');
          })
          .catch(console.error);
      } else {
        fetch('/api/pause', { method: 'POST' })
          .then(res => res.json())
          .then(() => {
            isRunning = false;
            el.iconPlay.innerHTML = '&#9658;';
            el.textPlay.textContent = 'Run';
            appendAuditLog('[SIM_PAUSE] Simulation execution paused.');
          })
          .catch(console.error);
      }
    });

    // Step (+1s)
    el.btnStep.addEventListener('click', () => {
      fetch('/api/step?dt=1.0', { method: 'POST' })
        .then(res => res.json())
        .then(frame => {
          handleTelemetryFrame(frame);
        })
        .catch(console.error);
    });

    // Reset
    el.btnReset.addEventListener('click', () => {
      fetch('/api/reset', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
          isRunning = false;
          el.iconPlay.innerHTML = '&#9658;';
          el.textPlay.textContent = 'Run';
          handleTelemetryFrame(data.frame);
          appendAuditLog('[SIM_RESET] Entire multi-agent digital twin reset to nominal baseline.');
        })
        .catch(console.error);
    });

    // Speed Selector
    el.selSpeed.addEventListener('change', () => {
      if (isRunning) {
        const speed = parseFloat(el.selSpeed.value);
        fetch(`/api/play?speed=${speed}`, { method: 'POST' }).catch(console.error);
      }
    });

    // Attack Injection
    el.btnInjectAttack.addEventListener('click', () => {
      const attackPayload = {
        attack_type: el.selAttackType.value,
        target_node: parseInt(el.selAttackTarget.value, 10),
        duration_s: parseFloat(el.inpAttackDuration.value),
        intensity: parseFloat(el.inpAttackIntensity.value),
        drop_probability: parseFloat(el.inpDropProb.value)
      };

      fetch('/api/attack/inject', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(attackPayload)
      })
        .then(res => res.json())
        .then(data => {
          handleTelemetryFrame(data.updated_frame);
          appendAuditLog(
            `[ATTACK_INJECTED] Vector=${attackPayload.attack_type} on Node #${attackPayload.target_node} (duration=${attackPayload.duration_s}s, intensity=${attackPayload.intensity}x)`,
            true
          );
        })
        .catch(console.error);
    });

    // Stop Attack
    el.btnStopAttack.addEventListener('click', () => {
      fetch('/api/attack/stop', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
          handleTelemetryFrame(data.updated_frame);
          appendAuditLog('[ATTACK_CANCELLED] All ongoing cyberattacks terminated immediately.');
        })
        .catch(console.error);
    });

    // Mitigation Actuation
    el.btnTriggerHealing.addEventListener('click', () => {
      const payload = {
        target_node: selectedNodeId,
        weight_profile: el.selWeightProfile.value,
        force_escalation: false
      };

      fetch('/api/heal/trigger', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
        .then(res => res.json())
        .then(data => {
          handleTelemetryFrame(data.updated_frame);
          appendAuditLog(
            `[MITIGATION_ACTUATED] Strategy=${data.audit.chosen_strategy_id} Action=${data.audit.action_type} Cost_J=${data.audit.multi_objective_cost_j}`
          );
        })
        .catch(console.error);
    });

    // Emergency Safety Rollback
    el.btnRollback.addEventListener('click', () => {
      fetch('/api/heal/rollback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: 'Operator Emergency Rollback Triggered' })
      })
        .then(res => res.json())
        .then(data => {
          handleTelemetryFrame(data.updated_frame);
          appendAuditLog(
            `[ROLLBACK_S_PRE] Safety rollback executed in ${data.details.elapsed_ms}ms! Restored: ${data.details.restored_components.join(', ')}`,
            true
          );
        })
        .catch(console.error);
    });
  }

  // --- 5.1 Next-Gen Dashboard Tab Navigation & Specialty Renderers ---
  let activeAdvModel = 'hardened';

  function initNextGenTabs() {
    const tabButtons = document.querySelectorAll('.nav-tab');
    const tabPanes = document.querySelectorAll('.tab-pane');

    tabButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        const targetTabId = btn.getAttribute('data-tab');
        if (!targetTabId) return;

        tabButtons.forEach(b => b.classList.remove('active'));
        tabPanes.forEach(p => p.classList.remove('active'));

        btn.classList.add('active');
        const targetPane = document.getElementById(targetTabId);
        if (targetPane) targetPane.classList.add('active');

        // Trigger on-demand fetches when tab opens
        if (targetTabId === 'tab-gnn-explainability') {
          fetchAttentionMatrix();
          fetchCounterfactuals();
        } else if (targetTabId === 'tab-hil-traces') {
          fetchHILTraces();
        } else if (targetTabId === 'tab-adversarial-defense') {
          fetchAdversarialData();
        } else if (targetTabId === 'tab-federated-learning') {
          fetchFederatedData();
        }
      });
    });

    // Sub-controls in GNN tab
    const cfSelect = document.getElementById('sel-cf-target-node');
    if (cfSelect) {
      cfSelect.addEventListener('change', () => {
        fetchCounterfactuals(parseInt(cfSelect.value, 10));
      });
    }

    const btnRefreshCf = document.getElementById('btn-refresh-cf');
    if (btnRefreshCf) {
      btnRefreshCf.addEventListener('click', () => {
        const node = cfSelect ? parseInt(cfSelect.value, 10) : 2;
        fetchCounterfactuals(node);
      });
    }

    // Adversarial controls
    const advSlider = document.getElementById('adv-epsilon-slider');
    const advVal = document.getElementById('adv-epsilon-val');
    const btnHardened = document.getElementById('btn-model-hardened');
    const btnStandard = document.getElementById('btn-model-standard');

    if (advSlider) {
      advSlider.addEventListener('input', () => {
        if (advVal) advVal.textContent = parseFloat(advSlider.value).toFixed(2);
        fetchAdversarialData();
      });
    }

    if (btnHardened && btnStandard) {
      btnHardened.addEventListener('click', () => {
        activeAdvModel = 'hardened';
        btnHardened.className = 'btn btn-primary';
        btnStandard.className = 'btn btn-secondary';
        const badge = document.getElementById('adv-status-badge');
        if (badge) {
          badge.textContent = 'MINIMAX HARDENED';
          badge.style.background = 'var(--accent-indigo)';
        }
        fetchAdversarialData();
      });

      btnStandard.addEventListener('click', () => {
        activeAdvModel = 'standard';
        btnHardened.className = 'btn btn-secondary';
        btnStandard.className = 'btn btn-primary';
        const badge = document.getElementById('adv-status-badge');
        if (badge) {
          badge.textContent = 'STANDARD BASELINE';
          badge.style.background = 'var(--accent-crimson)';
        }
        fetchAdversarialData();
      });
    }
  }

  function fetchAttentionMatrix() {
    fetch('/api/gnn/attention')
      .then(r => r.json())
      .then(data => {
        const body = document.getElementById('attention-table-body');
        const badge = document.getElementById('tab2-attack-indicator');
        const ratio = document.getElementById('tab2-bridge-ratio');
        const topEdges = document.getElementById('tab2-top-edges');
        const featContainer = document.getElementById('tab2-feature-attribution-container');

        if (badge) {
          badge.textContent = data.is_attack_active ? 'ATTACK ACTIVE' : 'NOMINAL';
          badge.style.background = data.is_attack_active ? 'var(--accent-crimson)' : 'var(--accent-emerald)';
        }
        if (ratio) ratio.textContent = `${data.bridge_amplification_ratio}x`;
        if (topEdges && data.top_attended_edges) {
          topEdges.textContent = data.top_attended_edges.map(e => `(${e.source} -> ${e.target}: ${e.weight})`).join(', ');
        }

        if (body && data.attention_matrix) {
          body.innerHTML = '';
          data.attention_matrix.forEach((row, i) => {
            const tr = document.createElement('tr');
            let rowHtml = `<th style="text-align: left; padding-left: 6px;">N${i}</th>`;
            row.forEach((val, j) => {
              const isBridge = (i === 2 && j === 3) || (i === 3 && j === 2) || (i === 0 && j === 2) || (i === 2 && j === 0);
              const bgAlpha = Math.min(0.9, Math.max(0.12, val * 2.2));
              const bgColor = isBridge && data.is_attack_active
                ? `rgba(239, 68, 68, ${bgAlpha})`
                : (isBridge ? `rgba(6, 182, 212, ${bgAlpha})` : `rgba(14, 165, 233, ${bgAlpha})`);
              const textColor = val > 0.25 ? '#ffffff' : '#cbd5e1';
              rowHtml += `<td style="background: ${bgColor}; color: ${textColor}; font-weight: ${isBridge ? '700' : '400'};" title="Edge (${i}, ${j}): ${val}">${val.toFixed(2)}</td>`;
            });
            tr.innerHTML = rowHtml;
            body.appendChild(tr);
          });
        }

        if (featContainer && data.feature_attribution) {
          featContainer.innerHTML = '';
          data.feature_attribution.forEach(f => {
            const row = document.createElement('div');
            row.style.display = 'flex';
            row.style.alignItems = 'center';
            row.style.gap = '8px';
            row.style.fontSize = '11px';
            row.innerHTML = `
              <span style="width: 140px; color: var(--text-muted);">${f.feature}</span>
              <div style="flex: 1; height: 6px; background: rgba(255,255,255,0.08); border-radius: 3px; overflow: hidden;">
                <div style="width: ${f.importance_pct}%; height: 100%; background: var(--accent-cyan);"></div>
              </div>
              <span style="width: 45px; text-align: right; font-family: monospace; color: var(--text-main);">${f.importance_pct}%</span>
            `;
            featContainer.appendChild(row);
          });
        }
      })
      .catch(console.error);
  }

  function fetchCounterfactuals(nodeId = 2) {
    fetch(`/api/gnn/counterfactual?node_id=${nodeId}`)
      .then(r => r.json())
      .then(data => {
        const container = document.getElementById('counterfactual-cards-container');
        if (!container || !data.worlds) return;

        container.innerHTML = '';
        const worldKeys = ['W0', 'W1', 'W2', 'W_star'];
        worldKeys.forEach(k => {
          const w = data.worlds[k];
          if (!w) return;
          const isChosen = (k === 'W_star');
          const card = document.createElement('div');
          card.className = `cf-card ${isChosen ? 'chosen' : ''}`;
          card.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <div>
                <strong style="color: ${isChosen ? 'var(--accent-emerald)' : 'var(--accent-cyan)'}; font-size: 13px;">${w.world_name} (${w.world_id})</strong>
                <div style="font-size: 10.5px; color: var(--text-dim);">${w.action_description}</div>
              </div>
              <span style="font-size: 11px; font-weight: 700; color: ${isChosen ? 'var(--accent-emerald)' : 'var(--text-muted)'}; background: rgba(255,255,255,0.05); padding: 3px 8px; border-radius: 4px;">
                TOPSIS: ${w.topsis_score.toFixed(3)}
              </span>
            </div>
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; margin-top: 6px; font-size: 10.5px; color: var(--text-muted);">
              <div>PDR: <strong style="color: var(--text-main);">${(w.pdr * 100).toFixed(1)}%</strong></div>
              <div>Latency: <strong style="color: var(--text-main);">${w.latency_ms.toFixed(1)}ms</strong></div>
              <div>Cost J: <strong style="color: var(--accent-amber);">${w.multi_objective_cost_j.toFixed(3)}</strong></div>
              <div>Admissible: <strong style="color: ${w.is_admissible ? 'var(--accent-emerald)' : 'var(--accent-crimson)'};">${w.is_admissible ? 'YES' : 'NO'}</strong></div>
            </div>
          `;
          container.appendChild(card);
        });
      })
      .catch(console.error);
  }

  function fetchHILTraces() {
    fetch('/api/gnn/hil_trace')
      .then(r => r.json())
      .then(data => {
        const tracesContainer = document.getElementById('hil-traces-container');
        const hwContainer = document.getElementById('hil-hardware-container');

        if (tracesContainer && data.traces) {
          tracesContainer.innerHTML = '';
          data.traces.forEach(t => {
            const card = document.createElement('div');
            card.className = 'cf-card';
            card.innerHTML = `
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <strong style="color: var(--accent-cyan); font-size: 13px;">${t.dataset} Testbed Trace</strong>
                <span style="font-size: 10.5px; background: rgba(14, 165, 233, 0.15); color: var(--accent-cyan); padding: 2px 6px; border-radius: 4px;">${t.attack_type}</span>
              </div>
              <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-top: 6px; font-size: 11px;">
                <div>Accuracy: <strong style="color: var(--accent-emerald);">${t.accuracy}%</strong></div>
                <div>Macro F1: <strong style="color: var(--accent-cyan);">${t.macro_f1}%</strong></div>
                <div>Clean Pkts: <strong style="color: var(--text-main);">${t.clean_samples}</strong></div>
                <div>Attack Pkts: <strong style="color: var(--accent-amber);">${t.attack_samples}</strong></div>
              </div>
            `;
            tracesContainer.appendChild(card);
          });
        }

        if (hwContainer && data.hardware_profiles) {
          hwContainer.innerHTML = '';
          Object.keys(data.hardware_profiles).forEach(hwName => {
            const p = data.hardware_profiles[hwName];
            const card = document.createElement('div');
            card.className = 'cf-card';
            const pct = (p.total_closed_loop_ms / p.real_time_deadline_ms) * 100;
            card.innerHTML = `
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <strong style="color: var(--text-main); font-size: 13px;">${hwName}</strong>
                <span style="font-size: 11px; font-weight: 700; color: var(--accent-emerald);">
                  ${p.total_closed_loop_ms} ms / ${p.real_time_deadline_ms} ms (${p.deadline_margin_pct}% margin)
                </span>
              </div>
              <div class="hw-progress-bar">
                <div class="hw-progress-fill" style="width: ${pct}%; background: ${pct < 50 ? 'var(--accent-emerald)' : 'var(--accent-amber)'};"></div>
              </div>
              <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 4px; margin-top: 8px; font-size: 10px; color: var(--text-dim);">
                <div>Feat: ${p.feature_extraction_ms}ms</div>
                <div>GNN: ${p.gnn_inference_ms}ms</div>
                <div>TOPSIS: ${p.topsis_optimization_ms}ms</div>
                <div>UART: ${p.uart_dispatch_ms}ms</div>
              </div>
            `;
            hwContainer.appendChild(card);
          });
        }
      })
      .catch(console.error);
  }

  function fetchAdversarialData() {
    const advSlider = document.getElementById('adv-epsilon-slider');
    const eps = advSlider ? parseFloat(advSlider.value) : 0.05;

    fetch(`/api/gnn/adversarial?epsilon=${eps}&model_type=${activeAdvModel}`)
      .then(r => r.json())
      .then(data => {
        const accEl = document.getElementById('adv-accuracy');
        const asrEl = document.getElementById('adv-asr');
        const maeEl = document.getElementById('adv-mae');
        const gainEl = document.getElementById('adv-gain');
        const accMeta = document.getElementById('adv-acc-meta');
        const asrMeta = document.getElementById('adv-asr-meta');

        if (accEl) accEl.textContent = `${data.accuracy.toFixed(1)}%`;
        if (asrEl) asrEl.textContent = `${data.attack_success_rate.toFixed(1)}%`;
        if (maeEl) maeEl.textContent = `${data.trust_mae.toFixed(4)}`;
        if (gainEl) gainEl.textContent = `+${data.robust_gain_pct.toFixed(1)}%`;
        if (accMeta) accMeta.textContent = `Model: ${data.model_type.toUpperCase()}`;
        if (asrMeta) asrMeta.textContent = data.is_defense_active ? 'Minimax Suppressed' : 'Vulnerable';
      })
      .catch(console.error);
  }

  function fetchFederatedData() {
    fetch('/api/gnn/federated')
      .then(r => r.json())
      .then(data => {
        const container = document.getElementById('federated-gateways-container');
        const accEl = document.getElementById('fed-acc');
        const payloadEl = document.getElementById('fed-payload');

        if (accEl && data.convergence) {
          accEl.textContent = `${data.convergence.fedgraphbridge_acc.toFixed(2)}%`;
        }
        if (payloadEl && data.communication_compression) {
          payloadEl.textContent = `${data.communication_compression.quantized_int8_payload_kb} KB`;
        }

        if (container && data.gateways) {
          container.innerHTML = '';
          data.gateways.forEach(gw => {
            const card = document.createElement('div');
            card.className = 'cf-card';
            card.innerHTML = `
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <strong style="color: var(--accent-cyan); font-size: 12px;">${gw.gateway_id}</strong>
                <span style="font-size: 10px; background: rgba(255,255,255,0.05); padding: 2px 6px; border-radius: 4px; color: var(--text-dim);">
                  ${gw.topology}
                </span>
              </div>
              <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; margin-top: 6px; font-size: 10.5px; color: var(--text-muted);">
                <div>Threat: <strong style="color: var(--accent-amber);">${gw.dominant_threat.split(' ')[0]}</strong></div>
                <div>Bridge: <strong style="color: var(--text-main);">${(gw.bridge_density * 100).toFixed(0)}%</strong></div>
                <div>Loss: <strong style="color: var(--accent-crimson);">${gw.loss}</strong></div>
                <div>Samples: <strong style="color: var(--accent-emerald);">${gw.local_samples}</strong></div>
              </div>
            `;
            container.appendChild(card);
          });
        }
      })
      .catch(console.error);
  }

  // --- 6. Bootstrap Initial State ---
  window.addEventListener('DOMContentLoaded', () => {
    initCharts();
    bindEventHandlers();
    initNextGenTabs();
    connectWebSocket();

    // Fetch initial frame in case WebSocket connection is delayed
    fetch('/api/state')
      .then(res => res.json())
      .then(frame => {
        handleTelemetryFrame(frame);
      })
      .catch(console.error);

    // Initial fetch for next-gen panels
    fetchAttentionMatrix();
    fetchCounterfactuals(2);
    fetchHILTraces();
    fetchAdversarialData();
    fetchFederatedData();
  });

})();
