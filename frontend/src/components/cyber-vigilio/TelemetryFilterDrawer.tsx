import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Icon } from '../Icon'

interface TelemetryFilterDrawerProps {
  isOpen: boolean
  onClose: () => void
  onApplyFilters: (filters: any) => void
}

export function TelemetryFilterDrawer({
  isOpen,
  onClose,
  onApplyFilters,
}: TelemetryFilterDrawerProps) {
  const [bioWindowBuffer, setBioWindowBuffer] = useState(15)
  const [courierWeightCap, setCourierWeightCap] = useState(40)
  const [autonomousAggression, setAutonomousAggression] = useState<'high' | 'balanced' | 'manual'>('high')
  const [autoRerouteSurge, setAutoRerouteSurge] = useState(true)
  const [selectedHubs, setSelectedHubs] = useState<string[]>(['Banquet Hall A', 'City Pharmacy', 'Hostel Mess'])
  const [selectedCargo, setSelectedCargo] = useState<string[]>(['Cooked Meals', 'Medical Cold-Chain', 'Raw Rations'])

  if (!isOpen) return null

  const toggleHub = (hub: string) => {
    setSelectedHubs((prev) =>
      prev.includes(hub) ? prev.filter((h) => h !== hub) : [...prev, hub]
    )
  }

  const toggleCargo = (cargo: string) => {
    setSelectedCargo((prev) =>
      prev.includes(cargo) ? prev.filter((c) => c !== cargo) : [...prev, cargo]
    )
  }

  const handleApply = () => {
    onApplyFilters({
      bioWindowBuffer,
      courierWeightCap,
      autonomousAggression,
      autoRerouteSurge,
      selectedHubs,
      selectedCargo,
    })
    onClose()
  }

  return (
    <AnimatePresence>
      <div className="cyber-modal-backdrop" onClick={onClose}>
        <motion.div
          className="cyber-filter-drawer"
          onClick={(e) => e.stopPropagation()}
          initial={{ x: '100%', opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: '100%', opacity: 0 }}
          transition={{ type: 'spring', damping: 28, stiffness: 300 }}
        >
          {/* Header */}
          <div className="drawer-header">
            <div className="drawer-header-left">
              <Icon name="settings" size={16} />
              <div>
                <h3>Telemetry & Solver Parameters</h3>
                <p>Constraint thresholds, safety buffers, and autonomous decision limits</p>
              </div>
            </div>
            <button className="modal-close-btn" onClick={onClose} aria-label="Close drawer">
              <Icon name="x" size={15} />
            </button>
          </div>

          <div className="drawer-body">
            {/* 1. Bio-Window Buffer Slider */}
            <div className="filter-group">
              <div className="filter-label-row">
                <label>Minimum Safe Bio-Window Buffer</label>
                <span className="slider-val-badge">{bioWindowBuffer} minutes</span>
              </div>
              <input
                type="range"
                min="5"
                max="45"
                step="5"
                value={bioWindowBuffer}
                onChange={(e) => setBioWindowBuffer(Number(e.target.value))}
                className="cyber-slider"
              />
              <small className="filter-hint">
                Emergency contingency buffer subtracted from transit deadline before triggering reroute.
              </small>
            </div>

            {/* 2. Courier Weight Limit Cap Slider */}
            <div className="filter-group">
              <div className="filter-label-row">
                <label>Volunteer Courier Carry Cap</label>
                <span className="slider-val-badge">{courierWeightCap} meals</span>
              </div>
              <input
                type="range"
                min="20"
                max="60"
                step="5"
                value={courierWeightCap}
                onChange={(e) => setCourierWeightCap(Number(e.target.value))}
                className="cyber-slider"
              />
              <small className="filter-hint">
                Enforces maximum physical capacity per single volunteer rider (Scenario 1 constraint).
              </small>
            </div>

            {/* 3. Autonomous Solver Aggression */}
            <div className="filter-group">
              <label>Constraint Solver Aggression Mode</label>
              <div className="mode-toggle-pill-row">
                <button
                  className={`mode-btn ${autonomousAggression === 'high' ? 'is-active' : ''}`}
                  onClick={() => setAutonomousAggression('high')}
                >
                  <Icon name="zap" size={12} />
                  <span>Full Autonomous</span>
                </button>
                <button
                  className={`mode-btn ${autonomousAggression === 'balanced' ? 'is-active' : ''}`}
                  onClick={() => setAutonomousAggression('balanced')}
                >
                  <Icon name="shield" size={12} />
                  <span>Balanced</span>
                </button>
                <button
                  className={`mode-btn ${autonomousAggression === 'manual' ? 'is-active' : ''}`}
                  onClick={() => setAutonomousAggression('manual')}
                >
                  <Icon name="target" size={12} />
                  <span>Operator Review</span>
                </button>
              </div>
            </div>

            {/* 4. Switch Toggles */}
            <div className="filter-group">
              <div className="toggle-switch-row">
                <div>
                  <strong>Auto-Reroute on Walk-In Surge</strong>
                  <p>Instantly divert in-transit cargo to verified fallback when shelter reaches 100%</p>
                </div>
                <button
                  className={`cyber-toggle-btn ${autoRerouteSurge ? 'is-checked' : ''}`}
                  onClick={() => setAutoRerouteSurge(!autoRerouteSurge)}
                >
                  <span className="toggle-thumb" />
                </button>
              </div>
            </div>

            {/* 5. Ingestion Hub Multi-Select */}
            <div className="filter-group">
              <label>Monitored Ingestion Hubs</label>
              <div className="chips-flex-row">
                {['Banquet Hall A', 'City Pharmacy', 'Hostel Mess', 'Central Hospital'].map((hub) => (
                  <button
                    key={hub}
                    className={`filter-chip ${selectedHubs.includes(hub) ? 'is-selected' : ''}`}
                    onClick={() => toggleHub(hub)}
                  >
                    {selectedHubs.includes(hub) && <Icon name="check" size={11} />}
                    <span>{hub}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* 6. Cargo Type Filter */}
            <div className="filter-group">
              <label>Perishable Cargo Classification</label>
              <div className="chips-flex-row">
                {['Cooked Meals', 'Medical Cold-Chain', 'Raw Rations', 'Water Reserves'].map((cargo) => (
                  <button
                    key={cargo}
                    className={`filter-chip ${selectedCargo.includes(cargo) ? 'is-selected' : ''}`}
                    onClick={() => toggleCargo(cargo)}
                  >
                    {selectedCargo.includes(cargo) && <Icon name="check" size={11} />}
                    <span>{cargo}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Drawer Footer */}
          <div className="drawer-footer">
            <button className="btn-cancel" onClick={onClose}>
              Cancel
            </button>
            <button className="btn-submit-orange" onClick={handleApply}>
              <Icon name="check" size={13} />
              <span>Apply Parameters</span>
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  )
}
