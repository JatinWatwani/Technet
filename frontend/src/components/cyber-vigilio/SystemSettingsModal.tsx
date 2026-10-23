import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Icon } from '../Icon'

interface SystemSettingsModalProps {
  isOpen: boolean
  onClose: () => void
  onExportAuditLog: () => void
  onResetSimulation: () => void
}

export function SystemSettingsModal({
  isOpen,
  onClose,
  onExportAuditLog,
  onResetSimulation,
}: SystemSettingsModalProps) {
  const [clockSpeed, setClockSpeed] = useState<'1x' | '5x' | '10x'>('1x')
  const [outboxSync, setOutboxSync] = useState(true)
  const [auditMode, setAuditMode] = useState<'strict' | 'relaxed'>('strict')

  if (!isOpen) return null

  return (
    <AnimatePresence>
      <div className="cyber-modal-backdrop" onClick={onClose}>
        <motion.div
          className="cyber-settings-modal"
          onClick={(e) => e.stopPropagation()}
          initial={{ opacity: 0, scale: 0.94, y: 16 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.94, y: 16 }}
          transition={{ duration: 0.22 }}
        >
          {/* Header */}
          <div className="modal-header">
            <div className="settings-header-title">
              <Icon name="settings" size={16} />
              <div>
                <h2>System & Backend Node Configuration</h2>
                <p>Authoritative clock, cluster sentinel endpoints, and transactional ledger</p>
              </div>
            </div>
            <button className="modal-close-btn" onClick={onClose} aria-label="Close settings">
              <Icon name="x" size={15} />
            </button>
          </div>

          <div className="settings-body">
            {/* Section 1: Active Cluster Nodes (Matching Dial Brands) */}
            <div className="settings-section">
              <h4>Active Cluster Nodes & Sentinels</h4>
              <div className="cluster-nodes-grid">
                <div className="cluster-node-item">
                  <div className="cluster-left">
                    <span className="node-live-dot" />
                    <strong>okta</strong>
                  </div>
                  <small>Cold-Chain Identity Sentinel</small>
                  <span className="status-badge green">ONLINE · 24ms</span>
                </div>

                <div className="cluster-node-item">
                  <div className="cluster-left">
                    <span className="node-live-dot" />
                    <strong>APACHE</strong>
                  </div>
                  <small>Constraint Dependency Engine</small>
                  <span className="status-badge green">ACTIVE · Invariants OK</span>
                </div>

                <div className="cluster-node-item">
                  <div className="cluster-left">
                    <span className="node-live-dot" />
                    <strong>VULTR</strong>
                  </div>
                  <small>Origin Perishable Pool</small>
                  <span className="status-badge green">INGESTING · 180 Meals</span>
                </div>

                <div className="cluster-node-item">
                  <div className="cluster-left">
                    <span className="node-live-dot warning" />
                    <strong>aws</strong>
                  </div>
                  <small>Shelter A Receiving Node</small>
                  <span className="status-badge orange">CAPACITY 50/50 FULL</span>
                </div>

                <div className="cluster-node-item full-width">
                  <div className="cluster-left">
                    <span className="node-live-dot" />
                    <strong>Alibaba Cloud</strong>
                  </div>
                  <small>Relief Camp B Fallback Destination (Standing by)</small>
                  <span className="status-badge green">READY · 58/138 Capacity</span>
                </div>
              </div>
            </div>

            {/* Section 2: Authoritative Clock Speed */}
            <div className="settings-section">
              <h4>Authoritative Simulation Clock</h4>
              <p className="section-subtext">
                Accelerates bio-decay and travel physics for deterministic testing without altering real timestamps.
              </p>
              <div className="clock-speed-row">
                <button
                  className={`clock-speed-btn ${clockSpeed === '1x' ? 'is-active' : ''}`}
                  onClick={() => setClockSpeed('1x')}
                >
                  <Icon name="clock" size={13} />
                  <span>1x Real-Time (Live Operations)</span>
                </button>
                <button
                  className={`clock-speed-btn ${clockSpeed === '5x' ? 'is-active' : ''}`}
                  onClick={() => setClockSpeed('5x')}
                >
                  <Icon name="zap" size={13} />
                  <span>5x Accelerated Clock</span>
                </button>
                <button
                  className={`clock-speed-btn ${clockSpeed === '10x' ? 'is-active' : ''}`}
                  onClick={() => setClockSpeed('10x')}
                >
                  <Icon name="activity" size={13} />
                  <span>10x Stress Simulation</span>
                </button>
              </div>
            </div>

            {/* Section 3: Invariant Audit Outbox */}
            <div className="settings-section">
              <h4>PostgreSQL Transactional Outbox & Invariant Mode</h4>
              <div className="toggle-switch-row">
                <div>
                  <strong>Strict Mass Conservation Invariant</strong>
                  <p>Guarantees zero quantity loss: sum(q_allocated) == sum(q_original)</p>
                </div>
                <button
                  className={`cyber-toggle-btn ${auditMode === 'strict' ? 'is-checked' : ''}`}
                  onClick={() => setAuditMode(auditMode === 'strict' ? 'relaxed' : 'strict')}
                >
                  <span className="toggle-thumb" />
                </button>
              </div>
            </div>
          </div>

          {/* Footer Actions */}
          <div className="settings-footer">
            <button className="btn-secondary-reset" onClick={onResetSimulation}>
              <Icon name="refresh" size={13} />
              <span>Reset Scenarios</span>
            </button>
            <div className="footer-right-actions">
              <button className="btn-cancel" onClick={onClose}>
                Close
              </button>
              <button className="btn-submit-orange" onClick={onExportAuditLog}>
                <Icon name="arrowDown" size={13} />
                <span>Export Forensic Audit (JSON)</span>
              </button>
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  )
}
