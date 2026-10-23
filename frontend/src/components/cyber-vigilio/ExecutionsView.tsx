import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Icon } from '../Icon'
import { ResolutionAuditModal, ResolutionAuditDetails } from './ResolutionAuditModal'

interface ExecutionsViewProps {
  onRunPlaybook1: () => void
  onRunPlaybook2: () => void
  onRunPlaybook3: () => void
  onToggleWater: () => void
  splitComplete: boolean
  rerouteResolved: boolean
  waterOnline: boolean
}

export function ExecutionsView({
  onRunPlaybook1,
  onRunPlaybook2,
  onRunPlaybook3,
  onToggleWater,
  splitComplete,
  rerouteResolved,
  waterOnline,
}: ExecutionsViewProps) {
  const [activePlaybook, setActivePlaybook] = useState<string>('/01')
  const [ledgerFilter, setLedgerFilter] = useState<'ALL' | 'COMMITTED' | 'RECONCILED' | 'VERIFIED'>('ALL')
  const [searchQuery, setSearchQuery] = useState<string>('')
  const [selectedAudit, setSelectedAudit] = useState<ResolutionAuditDetails | null>(null)
  const [isAuditModalOpen, setIsAuditModalOpen] = useState(false)
  const [isSimulating, setIsSimulating] = useState(false)

  const PLAYBOOKS = [
    {
      id: '/01',
      title: 'Oversized Batch Splitting Engine',
      desc: 'Enforces volunteer 40-unit maximum weight limit. Partitions large commercial surplus batches into parallel custody sub-tickets.',
      invariant: 'Conservation of Mass: original == sum(sub_tickets)',
      status: splitComplete ? 'Committed (5 Sub-Tickets)' : 'Ready for Trigger',
      badgeColor: '#18B880',
      actionLabel: splitComplete ? '✓ 180 = 180 Allocated' : 'Execute Batch Split (Cap 40)',
      handler: onRunPlaybook1,
      formula: '180 Portions = 40 + 40 + 40 + 40 + 20 [Loss: 0]',
      speed: '0.4s',
    },
    {
      id: '/02',
      title: 'Ghost Lease Revocation Worker',
      desc: 'Monitors volunteer claim heartbeats. At T = 00:00, unacknowledged unpicked allocations are reclaimed without double-booking.',
      invariant: 'Exclusivity: Unpicked inventory returns to pool immediately.',
      status: 'Active · Heartbeat Sentinel Online',
      badgeColor: '#F9771D',
      actionLabel: 'Simulate Rider Stall (T = 00:00)',
      handler: onRunPlaybook2,
      formula: 'Claim Expiration: Allocation #12 ──► Reclaimed to Master Pool',
      speed: '0.2s',
    },
    {
      id: '/03',
      title: 'In-Transit Custody Preservation Reroute',
      desc: 'Guarantees physical safety when destination shelter reaches capacity mid-journey. In-transit cargo is never discarded or unallocated.',
      invariant: 'Physical Custody: In-transit cargo cannot be unallocated.',
      status: rerouteResolved ? 'Resolved (Relief Camp B Locked)' : 'Surge Detected (Shelter A)',
      badgeColor: rerouteResolved ? '#18B880' : '#CE6969',
      actionLabel: rerouteResolved ? '✓ Reroute Locked (+40 Meals)' : 'Execute Reroute to Relief Camp B',
      handler: onRunPlaybook3,
      formula: 'Shelter A (50/50 Full) ──► Diverted to Relief Camp B (+1.4km)',
      speed: '1.6s',
    },
    {
      id: '/04',
      title: 'Supply Dependency Precondition Guard',
      desc: 'Enforces hard prerequisite checks before raw ration consignment release. Cooking requires clean potable water at destination hub.',
      invariant: 'Prerequisite Guard: Raw rations blocked unless water == true.',
      status: waterOnline ? 'Prerequisite Satisfied (Water Online)' : 'Dispatch Blocked (Missing Water)',
      badgeColor: waterOnline ? '#18B880' : '#CE6969',
      actionLabel: waterOnline ? 'Potable Water Verified (Simulate Outage)' : 'Restore Potable Water',
      handler: onToggleWater,
      formula: 'Shelter C Potable Water: ' + (waterOnline ? 'VERIFIED ✓' : 'OFFLINE ⚠'),
      speed: '0.6s',
    },
  ]

  const AUDIT_LOGS = [
    {
      id: 'TXN-9021',
      timestamp: '14:28:12',
      playbook: '/03 Mid-Transit Reroute',
      actor: 'Vigilio Constraint Solver #03',
      action: 'Rerouted Courier #07 (40 Cooked Meals) from Shelter A to Relief Camp B inside 19m safe window',
      hash: 'sha256: 9b2d8f7e1a3c5690b8f411cd',
      status: 'COMMITTED',
      details: {
        incidentId: 'TXN-9021',
        title: 'Courier #07 Physical Custody Reroute',
        severity: 'Critical',
        source: 'Banquet Hall A',
        destination: 'Relief Camp B (Capacity 138)',
        cargo: '40 Portions Hot Meals',
        rootCause: 'Shelter A capped at 50/50 capacity. Walk-in surge triggered dynamic divert.',
        invariantTested: 'Physical Custody Invariant: Conservation of Mass holds strictly.',
        algorithmicAction: 'Diverted courier along Eastern Arterial. Locked bio-safe margin at 19 minutes.',
        custodyProof: 'SHA256: 9b2d8f7e1a3c5690b8f411cd | verified=true',
        safeBioWindowRemaining: '19m safe margin',
        recoveryTimeSeconds: 1.6,
      },
    },
    {
      id: 'TXN-9018',
      timestamp: '14:24:05',
      playbook: '/01 Batch Splitting',
      actor: 'Inventory Ingestion Worker',
      action: 'Split Banquet Hall A 180 Meals into 5 sub-tickets (40+40+40+40+20). Invariant validated: 180 == 180',
      hash: 'sha256: 3a71b80f92cd3412aa8910be',
      status: 'COMMITTED',
      details: {
        incidentId: 'TXN-9018',
        title: '180-Meal Commercial Batch Partition',
        severity: 'High',
        source: 'Banquet Hall A',
        destination: 'Distributed Courier Pool',
        cargo: '180 Cooked Meals',
        rootCause: 'Commercial batch exceeds 40-unit bike carry cap.',
        invariantTested: 'Mass Conservation: sum(allocations) == 180.',
        algorithmicAction: 'Created 5 custody sub-tickets with independent heartbeat leases.',
        custodyProof: 'SHA256: 3a71b80f92cd3412aa8910be | zero_loss=true',
        safeBioWindowRemaining: '48m safe margin',
        recoveryTimeSeconds: 0.4,
      },
    },
    {
      id: 'TXN-9014',
      timestamp: '14:18:42',
      playbook: '/02 Lease Revocation',
      actor: 'Heartbeat Sentinel Monitor',
      action: 'Rider #12 heartbeat timeout at 00:00. Revoked lease and returned 40 portions to Master Pool',
      hash: 'sha256: 77b10ac489fe203498b2110c',
      status: 'RECONCILED',
      details: {
        incidentId: 'TXN-9014',
        title: 'Ghost Lease Revocation on Stall',
        severity: 'High',
        source: 'Central Depot',
        destination: 'Reclaimed to Pool',
        cargo: '40 Perishable Meals',
        rootCause: 'Volunteer rider stalled. Claim heartbeat expired at 00:00.',
        invariantTested: 'Exclusivity Invariant: Zero double booking.',
        algorithmicAction: 'Lease revoked automatically and reassigned to active backup rider.',
        custodyProof: 'SHA256: 77b10ac489fe203498b2110c | reclaimed=true',
        safeBioWindowRemaining: 'Safe in pool',
        recoveryTimeSeconds: 0.2,
      },
    },
    {
      id: 'TXN-9009',
      timestamp: '14:12:00',
      playbook: '/04 Prerequisite Guard',
      actor: 'Dependency Rule Guard',
      action: 'Verified Shelter C potable water telemetry sensor online. Approved 96 raw ration portions',
      hash: 'sha256: 12de940fa781bc099128fe00',
      status: 'VERIFIED',
      details: {
        incidentId: 'TXN-9009',
        title: 'Potable Water Sentinel Verification',
        severity: 'Medium',
        source: 'Hostel Mess',
        destination: 'Shelter C Cooking Station',
        cargo: '96 Raw Ration Kits',
        rootCause: 'Cooking raw rations strictly requires clean water sensor verification.',
        invariantTested: 'Prerequisite Guard Invariant.',
        algorithmicAction: 'Sensor online: approved dispatch gate.',
        custodyProof: 'SHA256: 12de940fa781bc099128fe00 | water_online=true',
        safeBioWindowRemaining: '120m dry storage',
        recoveryTimeSeconds: 0.6,
      },
    },
  ]

  const handleRowClick = (details: ResolutionAuditDetails) => {
    setSelectedAudit(details)
    setIsAuditModalOpen(true)
  }

  const handleRunAllDemo = () => {
    setIsSimulating(true)
    onRunPlaybook1()
    setTimeout(() => {
      onRunPlaybook2()
      setTimeout(() => {
        onRunPlaybook3()
        setIsSimulating(false)
      }, 1000)
    }, 800)
  }

  const filteredLogs = AUDIT_LOGS.filter((l) => {
    if (ledgerFilter !== 'ALL' && l.status !== ledgerFilter) return false
    if (searchQuery.trim() === '') return true
    const q = searchQuery.toLowerCase()
    return (
      l.id.toLowerCase().includes(q) ||
      l.action.toLowerCase().includes(q) ||
      l.playbook.toLowerCase().includes(q) ||
      l.actor.toLowerCase().includes(q)
    )
  })

  return (
    <div className="executions-workspace">
      {/* Top Presentation Engine Status Strip */}
      <div className="executions-engine-strip">
        <div className="engine-meta-left">
          <span className="engine-status-pulse" />
          <div>
            <strong>Z3 Invariant Solver Engine v2.8 • Online</strong>
            <small>Deterministic tie-breaking • Mean solver latency: 1.6s • SHA-256 Ledger</small>
          </div>
        </div>

        <div className="engine-actions-right">
          <button
            className={`btn-demo-sim ${isSimulating ? 'is-simulating' : ''}`}
            onClick={handleRunAllDemo}
            disabled={isSimulating}
            title="Demonstrate end-to-end autonomous self-healing for presentation"
          >
            <Icon name="zap" size={13} />
            <span>{isSimulating ? 'Simulating Self-Healing...' : '▶ Run Autonomous Self-Healing Demo'}</span>
          </button>
        </div>
      </div>

      {/* Top Playbooks Grid (4 Equal Columns) */}
      <div className="executions-playbooks-grid">
        {PLAYBOOKS.map((pb) => {
          const isSelected = activePlaybook === pb.id
          return (
            <div
              key={pb.id}
              className={`playbook-card ${isSelected ? 'is-selected' : ''}`}
              onClick={() => setActivePlaybook(pb.id)}
            >
              <div className="playbook-top-row">
                <span className="pb-id-badge">{pb.id}</span>
                <span
                  className="pb-status-tag"
                  style={{ color: pb.badgeColor, backgroundColor: `${pb.badgeColor}18` }}
                >
                  {pb.status}
                </span>
              </div>

              <h4>{pb.title}</h4>
              <p className="pb-desc-text">{pb.desc}</p>

              <div className="pb-formula-box">
                <Icon name="activity" size={12} />
                <code>{pb.formula}</code>
              </div>

              <div className="pb-invariant-note">
                <Icon name="shield" size={12} />
                <span>{pb.invariant}</span>
              </div>

              <button
                className="pb-action-button"
                onClick={(e) => {
                  e.stopPropagation()
                  pb.handler()
                }}
              >
                <Icon name="zap" size={13} />
                <span>{pb.actionLabel}</span>
              </button>
            </div>
          )
        })}
      </div>

      {/* Transaction & Audit Ledger Stream */}
      <div className="executions-ledger-panel">
        <div className="panel-header-row">
          <div>
            <h3>Append-Only Autonomous Execution Ledger</h3>
            <p>Click any transaction row to inspect mathematical proof & cryptographic custody</p>
          </div>

          <div className="ledger-controls-row">
            <input
              type="text"
              className="ledger-search-input"
              placeholder="Filter by TXN, Courier, Action..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            <div className="ledger-filter-pills">
              {(['ALL', 'COMMITTED', 'RECONCILED', 'VERIFIED'] as const).map((s) => (
                <button
                  key={s}
                  className={`ledger-filter-pill ${ledgerFilter === s ? 'is-active' : ''}`}
                  onClick={() => setLedgerFilter(s)}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="table-responsive-container">
          <table className="executions-audit-table">
            <thead>
              <tr>
                <th>Txn ID</th>
                <th>Timestamp</th>
                <th>Playbook Rule</th>
                <th>Authoritative Worker</th>
                <th>Committed Operational Decision</th>
                <th>Cryptographic Invariant Hash</th>
                <th>State</th>
              </tr>
            </thead>
            <tbody>
              {filteredLogs.map((log) => (
                <tr
                  key={log.id}
                  onClick={() => handleRowClick(log.details)}
                  style={{ cursor: 'pointer' }}
                  title="Click to inspect cryptographic resolution audit"
                >
                  <td><span className="mono-id">{log.id}</span></td>
                  <td><span className="mono-time">{log.timestamp}</span></td>
                  <td><strong>{log.playbook}</strong></td>
                  <td><span className="actor-pill">{log.actor}</span></td>
                  <td>{log.action}</td>
                  <td><code className="hash-code">{log.hash}</code></td>
                  <td>
                    <span className={`status-tag-green ${log.status.toLowerCase()}`}>
                      <Icon name="check" size={11} />
                      <span>{log.status}</span>
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Forensic Audit Proof Modal */}
      {selectedAudit && (
        <ResolutionAuditModal
          isOpen={isAuditModalOpen}
          onClose={() => setIsAuditModalOpen(false)}
          details={selectedAudit}
          onConfirmResolution={() => setIsAuditModalOpen(false)}
        />
      )}
    </div>
  )
}
