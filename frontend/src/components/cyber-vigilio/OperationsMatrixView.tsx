import { useState } from 'react'
import { motion } from 'framer-motion'
import { Icon } from '../Icon'

interface OperationsMatrixViewProps {
  onClose: () => void
  onSplitBatch: () => void
  onStallRider: () => void
  onTriggerReroute: () => void
  onToggleWater: () => void
  splitComplete: boolean
  rerouteResolved: boolean
  waterOnline: boolean
}

export function OperationsMatrixView({
  onClose,
  onSplitBatch,
  onStallRider,
  onTriggerReroute,
  onToggleWater,
  splitComplete,
  rerouteResolved,
  waterOnline,
}: OperationsMatrixViewProps) {
  const [activeInventoryFilter, setActiveInventoryFilter] = useState<'all' | 'transit' | 'available'>('all')

  const INVENTORY_ROWS = [
    {
      batchId: 'BATCH-COOKED-01',
      donor: 'Banquet Hall A',
      cargo: 'Cooked Vegetable Biryani',
      original: 180,
      available: splitComplete ? 0 : 180,
      inTransit: splitComplete ? (rerouteResolved ? 40 : 180) : 0,
      delivered: rerouteResolved ? 140 : 0,
      loss: 0,
      safeWindow: '48m safe window',
      custody: rerouteResolved ? 'Delivered to Relief Camp B' : 'Courier #07 (40 units)',
    },
    {
      batchId: 'BATCH-INSULIN-02',
      donor: 'City Pharmacy Central',
      cargo: 'Cold-Chain Insulin Kits',
      original: 24,
      available: 0,
      inTransit: 24,
      delivered: 0,
      loss: 0,
      safeWindow: 'Cold-Chain 3.8°C',
      custody: 'Courier #02 & #05 (Dual Escort)',
    },
    {
      batchId: 'BATCH-RATIONS-03',
      donor: 'Hostel Mess Kitchen',
      cargo: 'Raw Grains & Lentil Kits',
      original: 96,
      available: waterOnline ? 0 : 96,
      inTransit: waterOnline ? 96 : 0,
      delivered: 0,
      loss: 0,
      safeWindow: '120m dry storage',
      custody: waterOnline ? 'In-Transit to Shelter C' : 'Held at Origin (Water Guard)',
    },
  ]

  const FLEET_COURIERS = [
    { id: 'Courier #07', vehicle: 'Motorcycle', custody: '40 Cooked Meals', destination: rerouteResolved ? 'Relief Camp B' : 'Shelter A', buffer: '19m left', status: rerouteResolved ? 'Delivered' : 'Rerouting' },
    { id: 'Courier #14', vehicle: 'Cargo E-Bike', custody: '60 Bread Kits', destination: 'Riverside Camp', buffer: '65m left', status: 'In Transit' },
    { id: 'Courier #02', vehicle: 'Insulated Van', custody: '24 Insulin Kits', destination: 'Relief Camp B', buffer: '42m left', status: 'Cold-Chain Safe' },
    { id: 'Courier #12', vehicle: 'Bicycle', custody: '0 units (Reclaimed)', destination: 'Shelter C', buffer: 'Revoked', status: 'Lease Revoked' },
    { id: 'Courier #09', vehicle: 'Motorcycle', custody: '35 Cooked Meals', destination: 'Shelter B', buffer: '34m left', status: 'In Transit' },
    { id: 'Courier #03', vehicle: 'Cargo Drone', custody: '15 Medical Kits', destination: 'Relief Camp B', buffer: '50m left', status: 'In Flight' },
  ]

  return (
    <motion.div
      className="operations-matrix-workspace"
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.98 }}
      transition={{ duration: 0.25 }}
    >
      {/* Matrix Header */}
      <div className="matrix-top-bar">
        <div className="matrix-title-wrap">
          <span className="matrix-tag">HIGH-DENSITY MATRIX</span>
          <h2>Integrated Operations Command Grid</h2>
          <p>Real-time authoritative inventory ledger, live courier fleet telemetry, and scenario injection</p>
        </div>
        <div className="matrix-top-actions">
          <button className="btn-exit-matrix" onClick={onClose}>
            <Icon name="x" size={13} />
            <span>Exit Grid Mode (Return to Dashboard)</span>
          </button>
        </div>
      </div>

      {/* Quick Scenario Injectors */}
      <div className="matrix-scenario-dock">
        <span className="dock-label">Deterministic Scenario Controls:</span>
        <button
          className={`dock-btn ${splitComplete ? 'is-complete' : ''}`}
          onClick={onSplitBatch}
        >
          <Icon name={splitComplete ? 'check' : 'plus'} size={12} />
          <span>{splitComplete ? 'Batch 180 Split (Locked)' : '1. Split 180-Meal Batch (Cap 40)'}</span>
        </button>

        <button className="dock-btn" onClick={onStallRider}>
          <Icon name="clock" size={12} />
          <span>2. Trigger Volunteer Stall (Lease 00:00)</span>
        </button>

        <button
          className={`dock-btn ${rerouteResolved ? 'is-complete' : 'is-action'}`}
          onClick={onTriggerReroute}
        >
          <Icon name="zap" size={12} />
          <span>{rerouteResolved ? '3. Shelter A Reroute Complete' : '3. Reroute Shelter A Walk-In Cargo'}</span>
        </button>

        <button
          className={`dock-btn ${waterOnline ? 'is-complete' : 'is-warning'}`}
          onClick={onToggleWater}
        >
          <Icon name={waterOnline ? 'check' : 'alert'} size={12} />
          <span>{waterOnline ? '4. Water Online at Shelter C' : '4. Water Offline (Block Rations)'}</span>
        </button>
      </div>

      {/* Dual Column Command Grid */}
      <div className="matrix-dual-grid">
        {/* Left Column: Authoritative Inventory Ledger */}
        <div className="matrix-panel">
          <div className="panel-header-row">
            <div>
              <h3>Authoritative Inventory Ledger</h3>
              <p>Quantity conservation: original == available + in_transit + delivered</p>
            </div>
            <span className="status-badge green">Ledger Invariant: 100% OK</span>
          </div>

          <div className="table-responsive-container">
            <table className="matrix-data-table">
              <thead>
                <tr>
                  <th>Batch / Cargo</th>
                  <th>Origin</th>
                  <th>Total</th>
                  <th>Avail</th>
                  <th>Transit</th>
                  <th>Delivered</th>
                  <th>Loss</th>
                  <th>Custody State</th>
                </tr>
              </thead>
              <tbody>
                {INVENTORY_ROWS.map((row) => (
                  <tr key={row.batchId}>
                    <td>
                      <strong>{row.cargo}</strong>
                      <small className="mono-sub">{row.batchId}</small>
                    </td>
                    <td>{row.donor}</td>
                    <td><strong>{row.original}</strong></td>
                    <td><span className="num-avail">{row.available}</span></td>
                    <td><span className="num-transit">{row.inTransit}</span></td>
                    <td><span className="num-delivered">{row.delivered}</span></td>
                    <td><span className="num-loss text-green">{row.loss}</span></td>
                    <td><span className="custody-tag">{row.custody}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right Column: Fleet Courier Tracking Grid */}
        <div className="matrix-panel">
          <div className="panel-header-row">
            <div>
              <h3>Active Volunteer Courier Telemetry</h3>
              <p>GPS tracking, custody verification, and bio-buffer monitors</p>
            </div>
            <span className="status-badge orange">6 Couriers Active</span>
          </div>

          <div className="table-responsive-container">
            <table className="matrix-data-table">
              <thead>
                <tr>
                  <th>Courier ID</th>
                  <th>Transport</th>
                  <th>Cargo Custody</th>
                  <th>Destination</th>
                  <th>Bio Buffer</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {FLEET_COURIERS.map((c) => (
                  <tr key={c.id}>
                    <td><strong>{c.id}</strong></td>
                    <td>{c.vehicle}</td>
                    <td>{c.custody}</td>
                    <td>{c.destination}</td>
                    <td><span className="buffer-mono">{c.buffer}</span></td>
                    <td>
                      <span className={`fleet-status-pill ${c.status === 'Delivered' ? 'green' : c.status === 'Rerouting' ? 'orange' : c.status === 'Lease Revoked' ? 'coral' : 'blue'}`}>
                        {c.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </motion.div>
  )
}
