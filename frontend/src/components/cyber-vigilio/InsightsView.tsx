import { useState } from 'react'
import { motion } from 'framer-motion'
import { Icon } from '../Icon'
import { SystemMetrics, Shelter } from '../../api/client'

interface InsightsViewProps {
  metrics?: SystemMetrics | null
  shelters?: Shelter[]
}

export function InsightsView({ metrics, shelters }: InsightsViewProps) {
  const [activeCurve, setActiveCurve] = useState<'all' | 'cooked' | 'insulin' | 'rations'>('all')

  const liveShelters = shelters && shelters.length > 0 ? shelters.map((s) => ({
    name: s.name,
    current: s.demand_remaining,
    capacity: s.receiving_capacity_remaining,
    status: s.status === 'CLOSED' ? 'CLOSED · Overflow' : `${s.demand_remaining >= s.receiving_capacity_remaining ? 'Full' : 'Available'}`,
    color: s.demand_remaining >= s.receiving_capacity_remaining ? '#CE6969' : '#18B880',
  })) : null

  const SHELTERS = liveShelters || [
    { name: 'Shelter A (Primary)', current: 50, capacity: 50, status: 'Full · Over capacity', color: '#CE6969' },
    { name: 'Relief Camp B (Fallback)', current: 58, capacity: 138, status: 'Healthy · Available', color: '#18B880' },
    { name: 'Shelter C (Cooking Station)', current: 65, capacity: 100, status: 'Water Sentinel Active', color: '#F9771D' },
    { name: 'Riverside Camp', current: 20, capacity: 80, status: 'Standby Reception', color: '#7b7d72' },
  ]

  const DECISION_DEADLINES = [
    {
      consignment: 'Banquet Hall A ──► Relief Camp B',
      cargo: 'Cooked Meals (40 portions)',
      courier: 'Courier #07',
      safeDeadline: '14:52:00',
      travelTime: '18 mins',
      handoffBuffer: '15 mins',
      lastSafeDecision: '14:19:00',
      status: 'Decision Executed (Rerouted)',
      urgency: 'green',
    },
    {
      consignment: 'City Pharmacy ──► Relief Camp B',
      cargo: 'Insulin Kits (24 units)',
      courier: 'Courier #02 & #05',
      safeDeadline: '15:20:00',
      travelTime: '22 mins',
      handoffBuffer: '20 mins',
      lastSafeDecision: '14:38:00',
      status: 'Cold-Chain Nominal (3.8°C)',
      urgency: 'green',
    },
    {
      consignment: 'Hostel Mess ──► Shelter C',
      cargo: 'Raw Ration Kits (96 units)',
      courier: 'Pending Dispatch',
      safeDeadline: '18:00:00',
      travelTime: '30 mins',
      handoffBuffer: '15 mins',
      lastSafeDecision: '16:15:00',
      status: 'Awaiting Water Prerequisite',
      urgency: 'orange',
    },
  ]

  return (
    <div className="insights-workspace">
      {/* Top Telemetry Strip */}
      <div className="insights-metrics-row">
        <div className="insight-metric-card">
          <span className="insight-eyebrow">Zero Spoilage Rate</span>
          <div className="insight-val-row">
            <span className="insight-big-val text-green">{metrics ? (metrics.inventory_spoiled_units === 0 ? '100%' : `${Math.round((1 - metrics.inventory_spoiled_units / Math.max(metrics.deliveries_completed, 1)) * 100)}%`) : '100%'}</span>
            <span className="insight-unit">Safe Handoff</span>
          </div>
          <small>{metrics ? `${metrics.deliveries_completed} deliveries verified inside biological window` : '4,700 units delivered inside biological safety window'}</small>
        </div>

        <div className="insight-metric-card">
          <span className="insight-eyebrow">Active Allocations</span>
          <div className="insight-val-row">
            <span className="insight-big-val">{metrics ? metrics.allocations_active : '1.6s'}</span>
            <span className="insight-unit">{metrics ? 'Live' : 'Decision Time'}</span>
          </div>
          <small>{metrics ? `${metrics.deliveries_in_transit} consignments in active custody transit` : 'Deterministic tie-breaking & constraint verification'}</small>
        </div>

        <div className="insight-metric-card">
          <span className="insight-eyebrow">Mass Conservation</span>
          <div className="insight-val-row">
            <span className="insight-big-val text-orange">{metrics ? (metrics.ledger_reconciliation_healthy ? '0 Loss' : 'Breach Detected') : '0 Loss'}</span>
            <span className="insight-unit">180 = 180</span>
          </div>
          <small>Mathematical verification: original == sum(allocated)</small>
        </div>

        <div className="insight-metric-card">
          <span className="insight-eyebrow">Active Open Incidents</span>
          <div className="insight-val-row">
            <span className="insight-big-val">{metrics ? metrics.incidents_active : '24.2'}</span>
            <span className="insight-unit">{metrics ? 'Exceptions' : 'km/h'}</span>
          </div>
          <small>{metrics ? `${metrics.batches_count} total inventory batches tracked in network` : '12 active GPS-verified volunteer couriers'}</small>
        </div>
      </div>

      {/* Main Charts Row */}
      <div className="insights-charts-grid">
        {/* Left: Spoilage Risk Curves (Multi-Line Spline) */}
        <div className="insights-panel chart-panel">
          <div className="panel-header-row">
            <div>
              <h3>Perishable Biological Decay Curves</h3>
              <p>Safe consumption probability vs elapsed transit time</p>
            </div>
            <div className="curve-filter-pills">
              <button
                className={`curve-pill ${activeCurve === 'all' ? 'is-active' : ''}`}
                onClick={() => setActiveCurve('all')}
              >
                All Perishables
              </button>
              <button
                className={`curve-pill ${activeCurve === 'cooked' ? 'is-active' : ''}`}
                onClick={() => setActiveCurve('cooked')}
              >
                Cooked Meals (48m)
              </button>
              <button
                className={`curve-pill ${activeCurve === 'insulin' ? 'is-active' : ''}`}
                onClick={() => setActiveCurve('insulin')}
              >
                Cold-Chain (3.8°C)
              </button>
            </div>
          </div>

          <div className="spline-chart-container">
            <svg viewBox="0 0 540 220" className="spline-svg" preserveAspectRatio="none">
              <defs>
                <linearGradient id="cooked-area-grad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#F9771D" stopOpacity="0.28" />
                  <stop offset="100%" stopColor="#F9771D" stopOpacity="0.0" />
                </linearGradient>
                <linearGradient id="insulin-area-grad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#18B880" stopOpacity="0.25" />
                  <stop offset="100%" stopColor="#18B880" stopOpacity="0.0" />
                </linearGradient>
              </defs>

              {/* Grid Lines */}
              <line x1="0" y1="40" x2="540" y2="40" stroke="rgba(27,26,38,0.06)" strokeDasharray="3 3" />
              <line x1="0" y1="90" x2="540" y2="90" stroke="rgba(27,26,38,0.06)" strokeDasharray="3 3" />
              <line x1="0" y1="140" x2="540" y2="140" stroke="rgba(27,26,38,0.06)" strokeDasharray="3 3" />
              <line x1="0" y1="190" x2="540" y2="190" stroke="rgba(27,26,38,0.08)" />

              {/* Curve 1: Cooked Meals (Rapid Decay after 45m) */}
              {(activeCurve === 'all' || activeCurve === 'cooked') && (
                <g>
                  <path
                    d="M 0 30 Q 120 35 220 70 T 360 140 T 480 185 L 540 195 L 540 220 L 0 220 Z"
                    fill="url(#cooked-area-grad)"
                  />
                  <path
                    d="M 0 30 Q 120 35 220 70 T 360 140 T 480 185 L 540 195"
                    fill="none"
                    stroke="#F9771D"
                    strokeWidth="2.8"
                    strokeLinecap="round"
                  />
                  <circle cx="220" cy="70" r="4.5" fill="#F9771D" stroke="#ffffff" strokeWidth="2" />
                  {/* Current Position Marker */}
                  <circle cx="360" cy="140" r="5" fill="#F9771D" stroke="#ffffff" strokeWidth="2" />
                </g>
              )}

              {/* Curve 2: Cold-Chain Insulin (Stable then sharp cliff) */}
              {(activeCurve === 'all' || activeCurve === 'insulin') && (
                <g>
                  <path
                    d="M 0 20 Q 180 22 320 35 T 440 90 T 540 160 L 540 220 L 0 220 Z"
                    fill="url(#insulin-area-grad)"
                  />
                  <path
                    d="M 0 20 Q 180 22 320 35 T 440 90 T 540 160"
                    fill="none"
                    stroke="#18B880"
                    strokeWidth="2.8"
                    strokeLinecap="round"
                  />
                  <circle cx="320" cy="35" r="4.5" fill="#18B880" stroke="#ffffff" strokeWidth="2" />
                </g>
              )}
            </svg>

            <div className="chart-legend-row">
              <div className="legend-item">
                <span className="legend-color-dot orange" />
                <span>Cooked Meals (48m Safe Bio-Window)</span>
              </div>
              <div className="legend-item">
                <span className="legend-color-dot green" />
                <span>Cold-Chain Insulin (Thermal Range: 2°–8°C)</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right: Shelter Capacity Balance */}
        <div className="insights-panel capacity-panel">
          <div className="panel-header-row">
            <div>
              <h3>Shelter Capacity Equilibrium</h3>
              <p>Receiving density and sanitary thresholds</p>
            </div>
          </div>

          <div className="shelter-capacity-bars">
            {SHELTERS.map((s) => {
              const pct = Math.round((s.current / s.capacity) * 100)
              return (
                <div key={s.name} className="shelter-cap-item">
                  <div className="cap-label-row">
                    <strong>{s.name}</strong>
                    <span className="cap-pct" style={{ color: s.color }}>
                      {s.current} / {s.capacity} ({pct}%)
                    </span>
                  </div>
                  <div className="cap-track">
                    <motion.div
                      className="cap-fill"
                      initial={{ width: 0 }}
                      animate={{ width: `${Math.min(pct, 100)}%` }}
                      transition={{ duration: 0.8, ease: 'easeOut' }}
                      style={{ backgroundColor: s.color }}
                    />
                  </div>
                  <span className="cap-status-sub">{s.status}</span>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* Bottom: Last-Safe-Decision Table */}
      <div className="insights-panel deadlines-panel">
        <div className="panel-header-row">
          <div>
            <h3>Last-Safe-Decision Deadline Matrix</h3>
            <p>Authoritative calculation: Latest Decision = Deadline − Travel − Handoff − Safety Buffer</p>
          </div>
        </div>

        <div className="table-responsive-container">
          <table className="insights-deadlines-table">
            <thead>
              <tr>
                <th>Active Consignment</th>
                <th>Cargo / Spec</th>
                <th>Escort Courier</th>
                <th>Bio Deadline</th>
                <th>Travel Est.</th>
                <th>Buffer</th>
                <th>Latest Decision</th>
                <th>Solver Outcome</th>
              </tr>
            </thead>
            <tbody>
              {DECISION_DEADLINES.map((d, i) => (
                <tr key={i}>
                  <td><strong>{d.consignment}</strong></td>
                  <td>{d.cargo}</td>
                  <td><span className="courier-badge">{d.courier}</span></td>
                  <td><span className="mono-time">{d.safeDeadline}</span></td>
                  <td>{d.travelTime}</td>
                  <td>{d.handoffBuffer}</td>
                  <td><strong className="mono-time text-orange">{d.lastSafeDecision}</strong></td>
                  <td>
                    <span className={`decision-status-pill ${d.urgency}`}>
                      {d.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
