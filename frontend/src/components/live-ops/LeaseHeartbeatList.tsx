import { motion } from 'framer-motion'
import { Icon } from '../Icon'
import { SectionHeading } from '../common/SectionHeading'
import type { Lease } from '../../types'

interface LeaseHeartbeatListProps {
  leases: Lease[]
  onStallRider: () => void
}

export function LeaseHeartbeatList({ leases, onStallRider }: LeaseHeartbeatListProps) {
  return (
    <section className="panel lease-panel">
      <SectionHeading
        icon="route"
        eyebrow="CLAIM LEASES"
        title="Rider heartbeats"
        action={
          <button className="outline-button" onClick={onStallRider}>
            <Icon name="pause" size={13} />
            Simulate stall (Rider #12)
          </button>
        }
      />

      <div className="panel-subline">
        <span>3 active claims</span>
        <span className="subline-dot" />
        <span>Physical custody stays locked</span>
      </div>

      <div className="lease-list">
        {leases.map((lease, index) => {
          const isRecovery = lease.status === 'Recovery'
          return (
            <motion.div
              key={lease.id}
              className={`lease-row ${isRecovery ? 'is-recovery' : ''}`}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3, delay: index * 0.06 }}
            >
              <div className={`rider-avatar ${lease.tone}`}>{lease.id}</div>
              <div className="lease-info">
                <div>
                  <strong>{lease.name}</strong>
                  <span className="lease-destination">
                    <Icon name="route" size={12} /> {lease.destination}
                  </span>
                </div>
                <div className="lease-progress">
                  <span style={{ width: `${lease.progress}%` }} />
                </div>
              </div>
              <div className="lease-time">
                <strong>{lease.time}</strong>
                <span>{isRecovery ? 'lease revoked' : lease.status}</span>
              </div>
            </motion.div>
          )
        })}
      </div>

      <div className="lease-note">
        <div className="note-icon">
          <Icon name="shield" size={15} />
        </div>
        <span>
          Unpicked inventory can recover automatically. Picked-up cargo cannot silently return to the pool.
        </span>
      </div>
    </section>
  )
}
