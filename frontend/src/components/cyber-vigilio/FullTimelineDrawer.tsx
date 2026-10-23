import { motion, AnimatePresence } from 'framer-motion'
import { Icon } from '../Icon'

interface TimelineEvent {
  timestamp: string
  title: string
  subtext: string
  hash: string
  category: 'reroute' | 'split' | 'stall' | 'guard'
  status: 'Committed' | 'Verified' | 'Revoked'
}

interface FullTimelineDrawerProps {
  isOpen: boolean
  onClose: () => void
}

const EVENTS: TimelineEvent[] = [
  {
    timestamp: 'Today · 13:42:11',
    title: 'Mid-Journey Shelter A Overflow Triggered',
    subtext: 'Walk-in donor filled capacity. Rider #07 carrying 40 meals transactionally rerouted to Shelter B within 19m buffer.',
    hash: '0x8f2a...7c91',
    category: 'reroute',
    status: 'Committed',
  },
  {
    timestamp: 'Today · 13:28:44',
    title: '180-Meal Consignment Batch Split',
    subtext: 'Banquet Hall surplus split into 5 sub-tickets (40+40+40+40+20). Mathematical quantity conservation verified.',
    hash: '0x3d14...b4e2',
    category: 'split',
    status: 'Verified',
  },
  {
    timestamp: 'Today · 13:14:02',
    title: 'Rider #12 Lease Revocation Executed',
    subtext: 'Heartbeat signal lost. Lease expired at 00:00. Unpicked inventory recovered into pool before cold-safe deadline.',
    hash: '0x99e1...15d8',
    category: 'stall',
    status: 'Revoked',
  },
  {
    timestamp: 'Today · 12:55:19',
    title: 'Shelter C Clean Water Dependency Enforced',
    subtext: 'Potable water supply verified. Raw rations and formula matches approved for safe dispatch.',
    hash: '0x44a7...9923',
    category: 'guard',
    status: 'Verified',
  },
]

export function FullTimelineDrawer({ isOpen, onClose }: FullTimelineDrawerProps) {
  if (!isOpen) return null

  return (
    <AnimatePresence>
      <div className="cyber-modal-backdrop" onClick={onClose}>
        <motion.div
          className="cyber-timeline-drawer"
          onClick={(e) => e.stopPropagation()}
          initial={{ x: '100%' }}
          animate={{ x: 0 }}
          exit={{ x: '100%' }}
          transition={{ type: 'spring', damping: 30, stiffness: 350 }}
        >
          {/* Drawer Header */}
          <div className="drawer-header">
            <div>
              <h2>Full Chain-of-Custody Timeline</h2>
              <p>Cryptographic, immutable ledger of all dispatch, reroute, and recovery actions.</p>
            </div>
            <button className="modal-close-btn" onClick={onClose} aria-label="Close drawer">
              <Icon name="x" size={16} />
            </button>
          </div>

          {/* Timeline Tree */}
          <div className="drawer-timeline-list">
            {EVENTS.map((item, i) => (
              <div key={i} className="timeline-tree-node">
                <div className="tree-line-indicator">
                  <span
                    className={`tree-dot ${
                      item.category === 'reroute'
                        ? 'is-orange'
                        : item.category === 'split'
                        ? 'is-green'
                        : item.category === 'stall'
                        ? 'is-coral'
                        : 'is-purple'
                    }`}
                  />
                  {i < EVENTS.length - 1 && <span className="tree-stem" />}
                </div>

                <div className="tree-card-content">
                  <div className="tree-meta-row">
                    <span className="tree-time">{item.timestamp}</span>
                    <span className="tree-hash">{item.hash}</span>
                  </div>
                  <h3>{item.title}</h3>
                  <p>{item.subtext}</p>
                  <div className="tree-footer-badge">
                    <span className="status-chip">{item.status}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  )
}
