import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Icon } from '../Icon'
import { ResolutionAuditModal, ResolutionAuditDetails } from './ResolutionAuditModal'

interface KeyAlertsViewProps {
  onTriggerReroute: () => void
  rerouteResolved: boolean
  waterOnline: boolean
  onToggleWater: () => void
  onOpenAlertsTable: () => void
}

export function KeyAlertsView({
  onTriggerReroute,
  rerouteResolved,
  waterOnline,
  onToggleWater,
  onOpenAlertsTable,
}: KeyAlertsViewProps) {
  const [filter, setFilter] = useState<'all' | 'critical' | 'reroutes' | 'dependencies'>('all')
  const [selectedAudit, setSelectedAudit] = useState<ResolutionAuditDetails | null>(null)
  const [isAuditModalOpen, setIsAuditModalOpen] = useState(false)

  const handleInspectResolution = (details: ResolutionAuditDetails) => {
    setSelectedAudit(details)
    setIsAuditModalOpen(true)
  }

  const AUDIT_DATA: Record<string, ResolutionAuditDetails> = {
    shelterA: {
      incidentId: 'ALT-104',
      title: 'Shelter A Walk-In Overflow (50/50 Full)',
      severity: 'Critical',
      source: 'Banquet Hall A',
      destination: rerouteResolved ? 'Relief Camp B (Rerouted)' : 'Shelter A (Over capacity)',
      cargo: 'Cooked Meals (40 portions in physical custody of Courier #07)',
      rootCause: 'Shelter A received unexpected walk-in influx. Capped at 50/50 sanitary maximum.',
      invariantTested: 'Invariant: Physical cargo in transit must not be unallocated or discarded. Conservation of Mass holds.',
      algorithmicAction: 'Constraint solver redirected Courier #07 to Relief Camp B (58/138 capacity) inside 19m safe bio-window.',
      custodyProof: 'SHA256: 9b2d8f7e1a3c5690b8f411cd... | status=COMMITTED | safe_margin=19m',
      safeBioWindowRemaining: '19m safe margin',
      recoveryTimeSeconds: 1.6,
    },
    insulin: {
      incidentId: 'ALT-103',
      title: 'Medical Cold-Chain Sentinel Check',
      severity: 'High',
      source: 'City Pharmacy',
      destination: 'Relief Camp B',
      cargo: 'Insulin Kits (24 units)',
      rootCause: 'Ambient road heat peaked at 31°C. Cold-chain active sentinel verification required.',
      invariantTested: 'Cold-Chain Invariant: Thermal container must maintain 2.0°C – 8.0°C continuously.',
      algorithmicAction: 'Internal sensor confirmed steady 3.8°C with dual escort riders. Zero spoilage risk.',
      custodyProof: 'SHA256: 44fa09e3bc812903ea8901cd... | temp=3.8C | verified=true',
      safeBioWindowRemaining: '42m bio-safe window',
      recoveryTimeSeconds: 0.8,
    },
    rations: {
      incidentId: 'ALT-101',
      title: 'Dependency Guard: Shelter C Clean Water Offline',
      severity: 'Medium',
      source: 'Hostel Mess',
      destination: 'Shelter C',
      cargo: 'Raw Ration Kits (96 units)',
      rootCause: 'Shelter C water filtration sensor offline. Cooking raw food without clean water is prohibited.',
      invariantTested: 'Prerequisite Rule Invariant: Consignment dispatch requires all prerequisites verified.',
      algorithmicAction: waterOnline
        ? 'Potable water verified restored at Shelter C. Gate opened for delivery.'
        : 'Dispatch held in staging until potable water supply confirmed at Shelter C.',
      custodyProof: 'SHA256: 12de940fa781bc099128fe00... | water_potable=' + waterOnline,
      safeBioWindowRemaining: '120m dry storage',
      recoveryTimeSeconds: 1.1,
    },
    ghostLease: {
      incidentId: 'ALT-102',
      title: 'Ghost Lease Revocation (Courier #12)',
      severity: 'High',
      source: 'Central Depot',
      destination: 'Shelter C',
      cargo: 'Perishable Consignment #12 (40 portions)',
      rootCause: 'Courier #12 missed claim acknowledgement heartbeat at 00:00.',
      invariantTested: 'Reservation Invariant: Unpicked expired inventory is automatically recovered into available pool.',
      algorithmicAction: 'Lease revoked at 00:00. Stock restored to Master Pool without loss or double-booking.',
      custodyProof: 'SHA256: 77b10ac489fe203498b2110c... | unpicked_reclaimed=true',
      safeBioWindowRemaining: 'Stock safe in pool',
      recoveryTimeSeconds: 0.4,
    },
  }

  return (
    <div className="key-alerts-workspace">
      {/* Top Status Bar */}
      <div className="alerts-kpi-bar">
        <div className="alert-kpi-item">
          <span className="kpi-num critical">{rerouteResolved ? '2' : '3'}</span>
          <span className="kpi-label">Critical Breaches</span>
        </div>
        <div className="alert-kpi-item">
          <span className="kpi-num high">2</span>
          <span className="kpi-label">Active Sentinel Checks</span>
        </div>
        <div className="alert-kpi-item">
          <span className="kpi-num medium">{waterOnline ? '0' : '1'}</span>
          <span className="kpi-label">Prerequisite Holds</span>
        </div>
        <div className="alert-kpi-item">
          <span className="kpi-num green">0</span>
          <span className="kpi-label">Unaccounted Losses</span>
        </div>
        <button className="kpi-action-btn" onClick={onOpenAlertsTable}>
          <Icon name="layers" size={13} />
          <span>Open Full Ledger Table</span>
        </button>
      </div>

      {/* Filter Chips Bar */}
      <div className="alerts-filter-strip">
        <span className="strip-label">Filter View:</span>
        <button
          className={`filter-strip-btn ${filter === 'all' ? 'is-active' : ''}`}
          onClick={() => setFilter('all')}
        >
          All Active Alerts
        </button>
        <button
          className={`filter-strip-btn ${filter === 'critical' ? 'is-active' : ''}`}
          onClick={() => setFilter('critical')}
        >
          Critical Only
        </button>
        <button
          className={`filter-strip-btn ${filter === 'reroutes' ? 'is-active' : ''}`}
          onClick={() => setFilter('reroutes')}
        >
          In-Transit Reroutes
        </button>
        <button
          className={`filter-strip-btn ${filter === 'dependencies' ? 'is-active' : ''}`}
          onClick={() => setFilter('dependencies')}
        >
          Dependency Blocks
        </button>
      </div>

      {/* Alert Cards Grid */}
      <div className="alerts-cards-grid">
        {/* Card 1: Shelter A Overflow (Scenario 3) */}
        {(filter === 'all' || filter === 'critical' || filter === 'reroutes') && (
          <div className={`alert-detail-card ${rerouteResolved ? 'is-resolved' : 'is-critical'}`}>
            <div className="alert-card-header">
              <div className="card-header-left">
                <span className={`sev-badge ${rerouteResolved ? 'green' : 'critical'}`}>
                  {rerouteResolved ? 'RESOLVED ✓' : 'CRITICAL'}
                </span>
                <span className="alert-mono-id">ALT-104</span>
                <h4>Shelter A | Walk-In Overflow (Capacity Capped at 50/50)</h4>
              </div>
              <span className="alert-time-chip">12m ago · 19m buffer</span>
            </div>

            <p className="alert-desc">
              Shelter A reached maximum safe density (50/50 capacity). Courier #07 (carrying 40 hot meals)
              is in physical custody mid-transit. Cargo cannot be released or discarded.
            </p>

            <div className="alert-route-pill">
              <span>Origin: Banquet Hall A</span>
              <span className="route-arrow">──►</span>
              <span className={rerouteResolved ? 'text-green' : 'text-orange'}>
                {rerouteResolved ? 'Relief Camp B (Reroute Committed)' : 'Shelter A (Over Capacity)'}
              </span>
            </div>

            <div className="alert-actions-row">
              {rerouteResolved ? (
                <button
                  className="btn-proof"
                  onClick={() => handleInspectResolution(AUDIT_DATA.shelterA)}
                >
                  <Icon name="check" size={13} />
                  <span>View Reroute Constraint Proof</span>
                </button>
              ) : (
                <button
                  className="btn-reroute-hero"
                  onClick={() => {
                    onTriggerReroute()
                    handleInspectResolution(AUDIT_DATA.shelterA)
                  }}
                >
                  <Icon name="zap" size={13} />
                  <span>Execute Reroute to Relief Camp B</span>
                </button>
              )}
              <button
                className="btn-details-text"
                onClick={() => handleInspectResolution(AUDIT_DATA.shelterA)}
              >
                Inspect Telemetry Evidence
              </button>
            </div>
          </div>
        )}

        {/* Card 2: Cold-Chain Sentinel Check */}
        {(filter === 'all' || filter === 'critical') && (
          <div className="alert-detail-card is-high">
            <div className="alert-card-header">
              <div className="card-header-left">
                <span className="sev-badge high">HIGH</span>
                <span className="alert-mono-id">ALT-103</span>
                <h4>Medical Cold-Chain Sentinel Telemetry | City Pharmacy</h4>
              </div>
              <span className="alert-time-chip">42m bio-safe window</span>
            </div>

            <p className="alert-desc">
              24 short-life insulin kits in transit to Relief Camp B. External ambient temperature 31°C.
              Continuous sensor verifies insulated thermal enclosure at 3.8°C with dual courier escort.
            </p>

            <div className="alert-route-pill">
              <span>Origin: City Pharmacy</span>
              <span className="route-arrow">──►</span>
              <span className="text-green">Relief Camp B · Temp: 3.8°C [Safe Range: 2.0°–8.0°C]</span>
            </div>

            <div className="alert-actions-row">
              <button
                className="btn-proof"
                onClick={() => handleInspectResolution(AUDIT_DATA.insulin)}
              >
                <Icon name="shield" size={13} />
                <span>Verify Thermal Invariant</span>
              </button>
            </div>
          </div>
        )}

        {/* Card 3: Supply Dependency Guard (Scenario 4) */}
        {(filter === 'all' || filter === 'dependencies') && (
          <div className={`alert-detail-card ${waterOnline ? 'is-resolved' : 'is-medium'}`}>
            <div className="alert-card-header">
              <div className="card-header-left">
                <span className={`sev-badge ${waterOnline ? 'green' : 'medium'}`}>
                  {waterOnline ? 'PREREQUISITE SATISFIED' : 'BLOCKED'}
                </span>
                <span className="alert-mono-id">ALT-101</span>
                <h4>Shelter C Dependency Rule Guard: Potable Water</h4>
              </div>
              <span className="alert-time-chip">120m dry storage</span>
            </div>

            <p className="alert-desc">
              96 Raw Ration Kits at Hostel Mess require clean drinking water at Shelter C before cooking.
              Dispatch is held at origin until potable water supply sensor confirms water pressure.
            </p>

            <div className="alert-route-pill">
              <span>Status: {waterOnline ? '✓ Clean Water Verified at Shelter C' : '⚠ Missing Potable Water at Shelter C'}</span>
            </div>

            <div className="alert-actions-row">
              <button
                className={`btn-toggle-water ${waterOnline ? 'is-online' : 'is-offline'}`}
                onClick={onToggleWater}
              >
                <Icon name={waterOnline ? 'check' : 'zap'} size={13} />
                <span>{waterOnline ? 'Water Restored (Click to Simulate Outage)' : 'Restore Clean Water Sensor'}</span>
              </button>
              <button
                className="btn-details-text"
                onClick={() => handleInspectResolution(AUDIT_DATA.rations)}
              >
                Inspect Dependency Graph
              </button>
            </div>
          </div>
        )}

        {/* Card 4: Ghost Lease Revocation (Scenario 2) */}
        {(filter === 'all' || filter === 'reroutes') && (
          <div className="alert-detail-card is-resolved">
            <div className="alert-card-header">
              <div className="card-header-left">
                <span className="sev-badge green">AUTO-RESOLVED ✓</span>
                <span className="alert-mono-id">ALT-102</span>
                <h4>Ghost Lease Revocation & Stock Reclaim | Central Depot</h4>
              </div>
              <span className="alert-time-chip">Expired at 00:00 · Reclaimed</span>
            </div>

            <p className="alert-desc">
              Volunteer Courier #12 stalled before pickup. Claim timer reached 00:00. Backend auto-revoked lease
              and returned 40 units back to Master Ingestion Pool without loss or double-booking.
            </p>

            <div className="alert-route-pill">
              <span>Consignment #12: 40 portions reassigned to standby Courier #14</span>
            </div>

            <div className="alert-actions-row">
              <button
                className="btn-proof"
                onClick={() => handleInspectResolution(AUDIT_DATA.ghostLease)}
              >
                <Icon name="check" size={13} />
                <span>View Expiration Audit Record</span>
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Resolution Modal */}
      <ResolutionAuditModal
        isOpen={isAuditModalOpen}
        onClose={() => setIsAuditModalOpen(false)}
        details={selectedAudit}
        onConfirmResolution={() => {}}
      />
    </div>
  )
}
