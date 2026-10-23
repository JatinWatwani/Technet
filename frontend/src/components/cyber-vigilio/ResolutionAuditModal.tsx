import { motion, AnimatePresence } from 'framer-motion'
import { Icon } from '../Icon'

export interface ResolutionAuditDetails {
  incidentId: string
  title: string
  severity: string
  source: string
  destination: string
  cargo: string
  rootCause: string
  invariantTested: string
  algorithmicAction: string
  custodyProof: string
  safeBioWindowRemaining: string
  recoveryTimeSeconds: number
}

interface ResolutionAuditModalProps {
  isOpen: boolean
  onClose: () => void
  details: ResolutionAuditDetails | null
  onConfirmResolution: (id: string) => void
}

export function ResolutionAuditModal({
  isOpen,
  onClose,
  details,
  onConfirmResolution,
}: ResolutionAuditModalProps) {
  if (!isOpen || !details) return null

  return (
    <AnimatePresence>
      <div className="cyber-modal-backdrop" onClick={onClose}>
        <motion.div
          className="cyber-audit-modal"
          onClick={(e) => e.stopPropagation()}
          initial={{ opacity: 0, scale: 0.94, y: 16 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.94, y: 16 }}
          transition={{ duration: 0.22 }}
        >
          {/* Header */}
          <div className="modal-header">
            <div className="audit-header-title">
              <span className="audit-check-icon">
                <Icon name="check" size={16} />
              </span>
              <div>
                <h2>Resolution & Invariant Verification</h2>
                <p>Cryptographic proof of custody, safety constraints, and quantity conservation</p>
              </div>
            </div>
            <button className="modal-close-btn" onClick={onClose} aria-label="Close modal">
              <Icon name="x" size={16} />
            </button>
          </div>

          {/* Incident Summary Pill */}
          <div className="audit-incident-summary">
            <div className="summary-left">
              <span className={`sev-tag ${details.severity.toLowerCase()}`}>
                {details.severity}
              </span>
              <strong className="summary-id">{details.incidentId}</strong>
              <span className="summary-title">{details.title}</span>
            </div>
            <span className="audit-window-badge">
              <Icon name="clock" size={12} />
              <span>{details.safeBioWindowRemaining}</span>
            </span>
          </div>

          {/* Audit Grid */}
          <div className="audit-evidence-grid">
            {/* Box 1: Root Cause & Constraint Breached */}
            <div className="evidence-card">
              <div className="evidence-header">
                <Icon name="alert" size={14} />
                <h4>1. Root Cause & Constraint Breached</h4>
              </div>
              <p>{details.rootCause}</p>
              <div className="evidence-meta">
                <span>Origin: {details.source}</span>
                <span>Target: {details.destination}</span>
              </div>
            </div>

            {/* Box 2: Mathematical Invariant Validated */}
            <div className="evidence-card">
              <div className="evidence-header">
                <Icon name="shield" size={14} />
                <h4>2. Invariant Verified (Backend Invariant)</h4>
              </div>
              <p>{details.invariantTested}</p>
              <div className="evidence-badge green-badge">
                <Icon name="check" size={11} />
                <span>Conservation Equation: Validated 100%</span>
              </div>
            </div>

            {/* Box 3: Algorithmic Resolution Applied */}
            <div className="evidence-card full-width">
              <div className="evidence-header">
                <Icon name="zap" size={14} />
                <h4>3. Algorithmic Resolution Applied (Constraint Solver)</h4>
              </div>
              <p className="resolution-action-text">{details.algorithmicAction}</p>
              <div className="resolution-metrics-row">
                <div className="res-metric">
                  <small>Cargo Consignment</small>
                  <strong>{details.cargo}</strong>
                </div>
                <div className="res-metric">
                  <small>Solver Decision Latency</small>
                  <strong>{details.recoveryTimeSeconds}s</strong>
                </div>
                <div className="res-metric">
                  <small>Physical Custody Status</small>
                  <strong className="text-emerald">Continuous & Verified</strong>
                </div>
              </div>
            </div>

            {/* Box 4: Chain-of-Custody Proof */}
            <div className="evidence-card full-width code-bg">
              <div className="evidence-header">
                <Icon name="layers" size={14} />
                <h4>4. Cryptographic Custody Proof & Transaction Hash</h4>
              </div>
              <code className="audit-hash-block">{details.custodyProof}</code>
            </div>
          </div>

          {/* Actions */}
          <div className="audit-modal-footer">
            <button className="btn-cancel" onClick={onClose}>
              Dismiss
            </button>
            <button
              className="btn-confirm-resolve"
              onClick={() => {
                onConfirmResolution(details.incidentId)
                onClose()
              }}
            >
              <Icon name="check" size={14} />
              <span>Confirm & Commit Resolution</span>
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  )
}
