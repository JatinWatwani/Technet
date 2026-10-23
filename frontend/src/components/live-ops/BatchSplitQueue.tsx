import { motion } from 'framer-motion'
import { Icon } from '../Icon'
import { SectionHeading } from '../common/SectionHeading'
import type { Batch } from '../../types'

interface BatchSplitQueueProps {
  batches: Batch[]
  splitComplete: boolean
  onCreateSplit: () => void
}

export function BatchSplitQueue({
  batches,
  splitComplete,
  onCreateSplit,
}: BatchSplitQueueProps) {
  return (
    <section className="panel batch-panel">
      <SectionHeading
        icon="layers"
        eyebrow="DISPATCH QUEUE"
        title="Active batches"
        action={
          <button className="text-button" onClick={onCreateSplit}>
            <Icon name="plus" size={14} />
            {splitComplete ? 'Re-split' : '+ 180-Meal Split'}
          </button>
        }
      />

      <div className="panel-subline">
        <span>3 live consignments</span>
        <span className="subline-dot" />
        <span>Next expiry in 48m</span>
      </div>

      <div className="batch-list">
        {batches.map((batch, index) => (
          <motion.article
            key={batch.id}
            className={`batch-card ${batch.accent}`}
            initial={{ opacity: 0, y: 12, filter: 'blur(4px)' }}
            animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
            transition={{ duration: 0.35, delay: index * 0.08 }}
            whileHover={{ y: -2 }}
          >
            <div className="batch-card-top">
              <div className="batch-icon">
                <Icon name={batch.icon} size={16} />
              </div>
              <span className="status-pill">{batch.status}</span>
              <button className="card-more" aria-label={`More actions for ${batch.name}`}>
                <Icon name="more" size={15} />
              </button>
            </div>

            <div className="batch-main">
              <div>
                <h3>
                  {batch.quantity} <small>units</small>
                </h3>
                <strong>{batch.name}</strong>
                <span>{batch.origin}</span>
              </div>
              <div className="batch-route-icon">
                <Icon name={batch.id === 'insulin' ? 'shield' : 'route'} size={23} />
              </div>
            </div>

            <p className="batch-detail">{batch.detail}</p>

            <div className="micro-progress">
              <span style={{ width: `${batch.progress}%` }} />
              <em>{batch.progress}% readiness</em>
            </div>
          </motion.article>
        ))}
      </div>

      {splitComplete && (
        <motion.div
          className="subticket-breakdown"
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          transition={{ duration: 0.4 }}
          style={{
            padding: '12px 14px',
            margin: '12px 0 6px 0',
            borderRadius: 14,
            background: 'rgba(226, 221, 255, 0.45)',
            border: '1px solid rgba(129, 113, 244, 0.25)',
            fontSize: '11px',
            color: '#34334a',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, fontWeight: 700 }}>
            <span>Sub-Ticket Math (Max 40/rider cap)</span>
            <span style={{ color: '#6854d9' }}>5 Riders Assigned</span>
          </div>
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
            <span style={{ padding: '3px 7px', background: '#fff', borderRadius: 8, fontWeight: 600 }}>T1: 40 meals → Shelter A</span>
            <span style={{ padding: '3px 7px', background: '#fff', borderRadius: 8, fontWeight: 600 }}>T2: 40 meals → Shelter B</span>
            <span style={{ padding: '3px 7px', background: '#fff', borderRadius: 8, fontWeight: 600 }}>T3: 40 meals → Shelter B</span>
            <span style={{ padding: '3px 7px', background: '#fff', borderRadius: 8, fontWeight: 600 }}>T4: 40 meals → Shelter C</span>
            <span style={{ padding: '3px 7px', background: '#fff', borderRadius: 8, fontWeight: 600 }}>T5: 20 meals → Shelter C</span>
          </div>
        </motion.div>
      )}

      <div className={`conservation-bar ${splitComplete ? 'is-complete' : ''}`}>
        <div className="conservation-icon">
          <Icon name={splitComplete ? 'check' : 'target'} size={14} />
        </div>
        <div>
          <strong>
            {splitComplete ? '180 total = 180 allocated' : 'Conservation check'}
          </strong>
          <span>
            {splitComplete
              ? '0 unaccounted · quantity conservation mathematically verified'
              : 'Click "+ 180-Meal Split" to prove quantity safety'}
          </span>
        </div>
        <span className="conservation-value">{splitComplete ? '100%' : '—'}</span>
      </div>
    </section>
  )
}
