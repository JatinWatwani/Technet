import { motion, AnimatePresence } from 'framer-motion'
import { Icon } from '../Icon'

interface FloatingIncidentModalProps {
  isOpen: boolean
  onClose: () => void
  onVerify?: () => void
}

export function FloatingIncidentModal({
  isOpen,
  onClose,
  onVerify,
}: FloatingIncidentModalProps) {
  return (
    <AnimatePresence>
      {isOpen && (
        <motion.aside
          className="incident-card"
          initial={{ opacity: 0, y: 30, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 20, scale: 0.95 }}
          transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
          role="dialog"
          aria-labelledby="incident-title"
        >
          <div className="incident-top">
            <span className="incident-badge">
              <Icon name="alert" size={13} />
              ACTIVE INCIDENT
            </span>
            <button onClick={onClose} aria-label="Close incident">
              <Icon name="x" size={16} />
            </button>
          </div>

          <h3 id="incident-title">Shelter A closed mid-journey</h3>
          <p>
            Rider #07 has physical custody of 40 meals. A transactional reroute to Shelter B is locked inside the 19m safe buffer.
          </p>

          <div className="incident-progress">
            <div>
              <span>Decision buffer</span>
              <strong>19m</strong>
            </div>
            <span className="incident-track">
              <i />
            </span>
          </div>

          <button
            className="verify-button"
            onClick={() => {
              onVerify?.()
              onClose()
            }}
          >
            Verify reroute <Icon name="arrowUp" size={14} />
          </button>
        </motion.aside>
      )}
    </AnimatePresence>
  )
}
