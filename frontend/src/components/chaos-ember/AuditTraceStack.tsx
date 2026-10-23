import { motion } from 'framer-motion'
import { Icon } from '../Icon'
import { SectionHeading } from '../common/SectionHeading'
import type { FeedEvent } from '../../types'

interface AuditTraceStackProps {
  events: FeedEvent[]
}

export function AuditTraceStack({ events }: AuditTraceStackProps) {
  return (
    <section className="panel audit-panel">
      <SectionHeading
        icon="book"
        eyebrow="CHAIN OF CUSTODY"
        title="Recovery trace"
        action={
          <button className="icon-button quiet" aria-label="More audit details">
            <Icon name="more" size={18} />
          </button>
        }
      />

      <div className="audit-list">
        {events.map((event, index) => (
          <motion.div
            key={`${event.time}-${index}`}
            className="audit-event"
            initial={{ opacity: 0, x: 8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3, delay: index * 0.05 }}
          >
            <div className={`audit-marker ${event.tone}`}>
              <Icon
                name={
                  event.tone === 'orange'
                    ? 'zap'
                    : event.tone === 'mint'
                    ? 'check'
                    : 'route'
                }
                size={13}
              />
            </div>
            <div className="audit-copy">
              <div>
                <strong>{event.title}</strong>
                <span>{event.time}</span>
              </div>
              <p>{event.detail}</p>
            </div>
          </motion.div>
        ))}
      </div>

      <button className="wide-outline-button">
        <Icon name="book" size={14} />
        Open full audit trail <Icon name="chevron" size={14} />
      </button>
    </section>
  )
}
