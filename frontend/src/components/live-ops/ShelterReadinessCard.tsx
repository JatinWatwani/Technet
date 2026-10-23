import { motion } from 'framer-motion'
import { Icon } from '../Icon'
import { SectionHeading } from '../common/SectionHeading'
import type { Shelter } from '../../types'

interface ShelterReadinessCardProps {
  shelters: Shelter[]
  waterOnline: boolean
  onCloseShelter: () => void
  onToggleWater: () => void
}

export function ShelterReadinessCard({
  shelters,
  waterOnline,
  onCloseShelter,
  onToggleWater,
}: ShelterReadinessCardProps) {
  return (
    <section className="panel shelter-panel">
      <SectionHeading
        icon="home"
        eyebrow="RECEIVING NETWORK"
        title="Shelter readiness"
        action={
          <button className="icon-button quiet" aria-label="Refresh shelter statuses">
            <Icon name="refresh" size={16} />
          </button>
        }
      />

      <div className="panel-subline">
        <span>Capacity ledger</span>
        <span className="subline-dot" />
        <span>Updated 14s ago</span>
      </div>

      <div className="shelter-list">
        {shelters.map((shelter, index) => {
          const isShelterA = shelter.name === 'Shelter A'
          return (
            <motion.div
              key={shelter.name}
              className="shelter-row"
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3, delay: index * 0.06 }}
            >
              <div className={`shelter-marker ${shelter.tone}`}>
                <Icon name="home" size={15} />
              </div>

              <div className="shelter-info">
                <div>
                  <strong>{shelter.name}</strong>
                  <span>{shelter.city}</span>
                </div>
                <div className="capacity-bar">
                  <span
                    style={{
                      width:
                        shelter.capacity.split(' / ')[1] === '50'
                          ? '100%'
                          : shelter.capacity.startsWith('18')
                          ? '13%'
                          : '47%',
                    }}
                  />
                </div>
                <small>
                  {shelter.capacity} · {shelter.demand}
                </small>
              </div>

              <div className="shelter-actions">
                <span className={`readiness-state ${shelter.tone}`}>
                  {shelter.state}
                </span>
                {isShelterA && (
                  <button
                    className="close-action"
                    onClick={onCloseShelter}
                    aria-label="Simulate walk-in donor filling Shelter A"
                    title="Simulate walk-in donor filling Shelter A"
                  >
                    <Icon name="x" size={13} />
                  </button>
                )}
              </div>
            </motion.div>
          )
        })}
      </div>

      <div className={`dependency-alert ${waterOnline ? '' : 'is-blocked'}`}>
        <div className="dependency-icon">
          <Icon name={waterOnline ? 'water' : 'alert'} size={15} />
        </div>
        <div>
          <strong>
            {waterOnline
              ? 'All prerequisites verified'
              : 'Dispatch blocked at Shelter C'}
          </strong>
          <span>
            {waterOnline
              ? 'Clean water + cooking fuel are verified for current matches.'
              : 'Missing clean water · raw rations automatically rerouted to Shelter B.'}
          </span>
        </div>
        <button
          className="tiny-toggle"
          onClick={onToggleWater}
          title="Toggle Clean Water prerequisite at Shelter C"
        >
          {waterOnline ? 'ON' : 'OFF'}
        </button>
      </div>
    </section>
  )
}
