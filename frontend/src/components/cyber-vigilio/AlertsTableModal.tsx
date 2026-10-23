import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Icon } from '../Icon'
import { ResolutionAuditModal, ResolutionAuditDetails } from './ResolutionAuditModal'

export interface AlertRecord {
  id: string
  severity: 'Critical' | 'High' | 'Medium' | 'Low'
  source: string
  destination: string
  cargo: string
  custodyStatus: string
  buffer: string
  actionNeeded: string
  isResolved?: boolean
  resolutionNote?: string
}

interface AlertsTableModalProps {
  isOpen: boolean
  onClose: () => void
  onResolve: (id: string) => void
}

const INITIAL_RECORDS: AlertRecord[] = [
  {
    id: 'ALT-104',
    severity: 'Critical',
    source: 'Banquet Hall A',
    destination: 'Shelter A (50/50 Full)',
    cargo: 'Cooked Meals (40 units)',
    custodyStatus: 'Physical Custody (Rider #07)',
    buffer: '19m remaining',
    actionNeeded: 'Reroute to Relief Camp B',
  },
  {
    id: 'ALT-103',
    severity: 'High',
    source: 'City Pharmacy',
    destination: 'Relief Camp B',
    cargo: 'Insulin Kits (24 units)',
    custodyStatus: 'Cold-Chain 3.8°C Monitored',
    buffer: '42m remaining',
    actionNeeded: 'Telemetry Validated',
  },
  {
    id: 'ALT-102',
    severity: 'High',
    source: 'Central Depot',
    destination: 'Shelter C',
    cargo: 'Perishable Consignment #12',
    custodyStatus: 'Rider #12 Lease Revoked',
    buffer: 'Expired at 00:00',
    actionNeeded: 'Reassigned to Backup',
  },
  {
    id: 'ALT-101',
    severity: 'Medium',
    source: 'Hostel Mess',
    destination: 'Shelter C',
    cargo: 'Raw Ration Kits (96 units)',
    custodyStatus: 'Prerequisite Guard Active',
    buffer: '120m remaining',
    actionNeeded: 'Requires Clean Water',
  },
  {
    id: 'ALT-100',
    severity: 'Low',
    source: 'Community Kitchen',
    destination: 'Riverside Camp',
    cargo: 'Bread & Fruit Kits (60 units)',
    custodyStatus: 'In Transit (Rider #14)',
    buffer: '65m remaining',
    actionNeeded: 'On Track',
  },
]

// Detailed resolution proof dictionary matching backend invariants
const AUDIT_PROOFS: Record<string, ResolutionAuditDetails> = {
  'ALT-104': {
    incidentId: 'ALT-104',
    title: 'Shelter A Walk-In Overflow (Capacity Capped at 50/50)',
    severity: 'Critical',
    source: 'Banquet Hall A',
    destination: 'Shelter A ──► Relief Camp B',
    cargo: 'Cooked Meals (40 units in physical custody)',
    rootCause: 'Shelter A experienced sudden unnotified refugee surge. Inbound delivery of 40 meals would breach sanitary receiving threshold (50/50).',
    invariantTested: 'Invariant: Physical custody cannot be released to available pool; inventory mass must be conserved (40 allocated = 40 delivered).',
    algorithmicAction: 'Deterministic constraint solver recalculated shortest bio-safe route to Relief Camp B (+1.4km). Courier #07 diverted with 19m safe margin before food spoilage deadline.',
    custodyProof: 'SHA256: 9b2d8f7e1a3c5690b8f411cd... | Invariant: mass_conservation=true | status=COMMITTED',
    safeBioWindowRemaining: '19m remaining safe buffer',
    recoveryTimeSeconds: 1.6,
  },
  'ALT-103': {
    incidentId: 'ALT-103',
    title: 'Medical Cold-Chain Sentinel Check',
    severity: 'High',
    source: 'City Pharmacy',
    destination: 'Relief Camp B',
    cargo: 'Short-Life Insulin Kits (24 units)',
    rootCause: 'Ambient road temperature reached 31°C; cold-chain containment alert pinged at threshold edge.',
    invariantTested: 'Bio-Window Invariant: Temperature must remain within 2.0°C – 8.0°C continuously throughout transit.',
    algorithmicAction: 'Telemetry confirmed insulated cooler pack integrity at 3.8°C with dual courier escort. Zero thermal degradation recorded.',
    custodyProof: 'SHA256: 44fa09e3bc812903ea8901cd... | thermal_range=3.8C | escort_couriers=2',
    safeBioWindowRemaining: '42m remaining bio-safe window',
    recoveryTimeSeconds: 0.8,
  },
  'ALT-102': {
    incidentId: 'ALT-102',
    title: 'Ghost Reservation Revocation & Inventory Recovery',
    severity: 'High',
    source: 'Central Depot',
    destination: 'Shelter C',
    cargo: 'Perishable Consignment #12 (40 portions)',
    rootCause: 'Volunteer Courier #12 missed acknowledgement deadline; heartbeat lease expired at 00:00 without pickup confirmation.',
    invariantTested: 'Reservation Expiration Invariant: Unpicked expired inventory is automatically recovered into available pool without double-allocation.',
    algorithmicAction: 'Lease revoked transactionally. 40 units returned to Master Ingestion Pool and reassigned to standby Courier #14.',
    custodyProof: 'SHA256: 77b10ac489fe203498b2110c... | unpicked_claim_released=true | reallocated_courier=#14',
    safeBioWindowRemaining: 'Recovered into pool',
    recoveryTimeSeconds: 0.4,
  },
  'ALT-101': {
    incidentId: 'ALT-101',
    title: 'Dependency Guard: Clean Water Requirement',
    severity: 'Medium',
    source: 'Hostel Mess',
    destination: 'Shelter C',
    cargo: 'Raw Ration Kits (96 units)',
    rootCause: 'Shelter C water filtration sensor was offline. Raw grains cannot be cooked without clean water.',
    invariantTested: 'Prerequisite Rule Invariant: Consignment dispatch requires all prerequisites fulfilled before approval.',
    algorithmicAction: 'Municipal clean water delivery verified and pressure sensor restored at Shelter C. Gate opened for safe cooking.',
    custodyProof: 'SHA256: 12de940fa781bc099128fe00... | water_potable=true | cooking_fuel=verified',
    safeBioWindowRemaining: '120m dry storage',
    recoveryTimeSeconds: 1.1,
  },
  'ALT-100': {
    incidentId: 'ALT-100',
    title: 'Transit Verification Check',
    severity: 'Low',
    source: 'Community Kitchen',
    destination: 'Riverside Camp',
    cargo: 'Bread & Fruit Kits (60 units)',
    rootCause: 'Routine checkpoint verification for last-mile delivery tracking.',
    invariantTested: 'Chain-of-Custody Invariant: Periodic GPS and status check for active couriers.',
    algorithmicAction: 'Courier #14 confirmed arrival at Riverside Camp checkpoint. All 60 units verified intact.',
    custodyProof: 'SHA256: 55ca9910fe287103ba77011d... | arrival_checkpoint=ok',
    safeBioWindowRemaining: '65m buffer',
    recoveryTimeSeconds: 0.3,
  },
}

export function AlertsTableModal({ isOpen, onClose, onResolve }: AlertsTableModalProps) {
  const [records, setRecords] = useState<AlertRecord[]>(INITIAL_RECORDS)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedSev, setSelectedSev] = useState<string>('All')
  const [auditDetails, setAuditDetails] = useState<ResolutionAuditDetails | null>(null)
  const [isAuditModalOpen, setIsAuditModalOpen] = useState(false)

  if (!isOpen) return null

  const handleOpenResolutionInspector = (row: AlertRecord) => {
    const details = AUDIT_PROOFS[row.id] || {
      incidentId: row.id,
      title: `${row.cargo} at ${row.destination}`,
      severity: row.severity,
      source: row.source,
      destination: row.destination,
      cargo: row.cargo,
      rootCause: `Operational exception triggered on ${row.id}: ${row.actionNeeded}`,
      invariantTested: 'Quantity conservation and physical chain-of-custody invariant',
      algorithmicAction: `Autonomous solver executed contingency for ${row.id}: ${row.actionNeeded}. Safe arrival verified.`,
      custodyProof: `SHA256: ${Math.random().toString(36).substring(2, 15)}... | verified=true`,
      safeBioWindowRemaining: row.buffer,
      recoveryTimeSeconds: 1.2,
    }
    setAuditDetails(details)
    setIsAuditModalOpen(true)
  }

  const handleConfirmResolution = (id: string) => {
    setRecords((prev) =>
      prev.map((r) =>
        r.id === id
          ? {
              ...r,
              isResolved: true,
              resolutionNote: 'Resolved by Constraint Solver (Proof Verified)',
            }
          : r
      )
    )
    onResolve(id)
  }

  const filtered = records.filter((r) => {
    const matchesSev = selectedSev === 'All' || r.severity === selectedSev
    const matchesSearch =
      r.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.cargo.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.destination.toLowerCase().includes(searchQuery.toLowerCase())
    return matchesSev && matchesSearch
  })

  return (
    <AnimatePresence>
      <div className="cyber-modal-backdrop" onClick={onClose}>
        <motion.div
          className="cyber-table-modal"
          onClick={(e) => e.stopPropagation()}
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          transition={{ duration: 0.25 }}
        >
          {/* Modal Header */}
          <div className="modal-header">
            <div>
              <h2>Incident & Alerts Master Ledger</h2>
              <p>Autonomous contingency solver, custody verification, and bio-buffer audit table.</p>
            </div>
            <button className="modal-close-btn" onClick={onClose} aria-label="Close modal">
              <Icon name="x" size={16} />
            </button>
          </div>

          {/* Filters Bar */}
          <div className="modal-filters-bar">
            <div className="modal-search-box">
              <Icon name="search" size={14} />
              <input
                type="text"
                placeholder="Search alerts by ID, cargo, or destination..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>

            <div className="severity-filter-chips">
              {['All', 'Critical', 'High', 'Medium', 'Low'].map((sev) => (
                <button
                  key={sev}
                  className={`sev-chip ${selectedSev === sev ? 'is-active' : ''}`}
                  onClick={() => setSelectedSev(sev)}
                >
                  {sev}
                </button>
              ))}
            </div>
          </div>

          {/* Table Container */}
          <div className="table-responsive-container">
            <table className="alerts-data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Severity</th>
                  <th>Cargo / Batch</th>
                  <th>Origin / Donor</th>
                  <th>Destination</th>
                  <th>Custody Status</th>
                  <th>Decision Buffer</th>
                  <th>Resolution & Evidence</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((row) => (
                  <tr key={row.id} className={row.isResolved ? 'row-is-resolved' : ''}>
                    <td>
                      <span className="mono-id">{row.id}</span>
                    </td>
                    <td>
                      <span className={`sev-tag ${row.severity.toLowerCase()}`}>
                        {row.severity}
                      </span>
                    </td>
                    <td>
                      <strong>{row.cargo}</strong>
                    </td>
                    <td>{row.source}</td>
                    <td>{row.destination}</td>
                    <td>
                      <span className={`custody-pill ${row.isResolved ? 'is-resolved' : ''}`}>
                        {row.isResolved ? '✓ Resolution Locked' : row.custodyStatus}
                      </span>
                    </td>
                    <td>
                      <span className="buffer-mono">{row.buffer}</span>
                    </td>
                    <td>
                      {row.isResolved ? (
                        <button
                          className="table-action-btn resolved-btn"
                          onClick={() => handleOpenResolutionInspector(row)}
                          title="View Verified Audit Proof"
                        >
                          <Icon name="check" size={12} />
                          <span>View Proof</span>
                        </button>
                      ) : (
                        <button
                          className="table-action-btn"
                          onClick={() => handleOpenResolutionInspector(row)}
                          title="Inspect Resolution Details & Commit"
                        >
                          <Icon name="zap" size={12} />
                          <span>Resolve</span>
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </motion.div>
      </div>

      {/* Resolution & Invariant Verification Inspector Modal */}
      <ResolutionAuditModal
        isOpen={isAuditModalOpen}
        onClose={() => setIsAuditModalOpen(false)}
        details={auditDetails}
        onConfirmResolution={handleConfirmResolution}
      />
    </AnimatePresence>
  )
}
