import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Icon } from '../Icon'

interface AutomationBentoCardProps {
  onRunPlaybook1: () => void // Scenario 1: Batch split
  onRunPlaybook2: () => void // Scenario 2: Stall rider
  onRunPlaybook3: () => void // Scenario 3: Mid-journey reroute
}

export function AutomationBentoCard({
  onRunPlaybook1,
  onRunPlaybook2,
  onRunPlaybook3,
}: AutomationBentoCardProps) {
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null)

  const PLAYBOOKS = [
    {
      num: '/01',
      title: 'Playbooks Complete',
      name: 'Oversized Batch Splitting',
      desc: 'Enforces 40-meal volunteer weight limit. Divides 180 units into 5 sub-tickets with 0 loss.',
      actionLabel: 'Execute Batch Split',
      handler: onRunPlaybook1,
      badge: 'Verified',
      badgeColor: '#18B880',
    },
    {
      num: '/02',
      title: 'Waiting for Analysis',
      name: 'Ghost Lease Revocation',
      desc: 'Monitors rider claim heartbeats. Revokes claim if stalled at 00:00 and recovers unpicked stock.',
      actionLabel: 'Simulate Rider Stall',
      handler: onRunPlaybook2,
      badge: 'Active',
      badgeColor: '#F9771D',
    },
    {
      num: '/03',
      title: 'Playbook Recommendations',
      name: 'Mid-Journey Shelter Reroute',
      desc: 'Protects physical custody when destination closes. Reroutes in-transit cargo to verified fallback.',
      actionLabel: 'Trigger Shelter Reroute',
      handler: onRunPlaybook3,
      badge: 'Recommended',
      badgeColor: '#CE6969',
    },
  ]

  const toggleExpand = (i: number) => {
    setExpandedIndex((prev) => (prev === i ? null : i))
  }

  return (
    <div className="cyber-bento-card card-automation">
      {/* Card Header */}
      <div className="card-header-row">
        <h3>Automation</h3>
        <button
          className="card-arrow-btn"
          onClick={() => setExpandedIndex(expandedIndex !== null ? null : 0)}
          title="Toggle Automation Inspector"
          aria-label="Toggle automation inspector"
        >
          <Icon name="arrowUp" size={13} />
        </button>
      </div>

      {/* Playbooks Stack */}
      <div className="playbooks-stack">
        {PLAYBOOKS.map((pb, i) => {
          const isExpanded = expandedIndex === i
          return (
            <div key={pb.num} className={`playbook-item ${isExpanded ? 'is-expanded' : ''}`}>
              <div className="playbook-summary-row" onClick={() => toggleExpand(i)}>
                <button className="playbook-chevron" aria-label="Expand playbook">
                  <motion.span
                    animate={{ rotate: isExpanded ? 90 : 0 }}
                    transition={{ duration: 0.2 }}
                  >
                    <Icon name="chevron" size={12} />
                  </motion.span>
                </button>
                <div className="playbook-titles">
                  <span className="pb-num">{pb.num}</span>
                  <span className="pb-title">{pb.title}</span>
                </div>
                <span
                  className="pb-badge"
                  style={{ color: pb.badgeColor, backgroundColor: `${pb.badgeColor}18` }}
                >
                  {pb.badge}
                </span>
              </div>

              {/* Collapsible details */}
              <AnimatePresence>
                {isExpanded && (
                  <motion.div
                    className="playbook-expanded-content"
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.25 }}
                  >
                    <strong>{pb.name}</strong>
                    <p>{pb.desc}</p>
                    <button
                      className="pb-trigger-btn"
                      onClick={(e) => {
                        e.stopPropagation()
                        pb.handler()
                      }}
                    >
                      <Icon name="zap" size={12} />
                      <span>{pb.actionLabel}</span>
                    </button>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )
        })}
      </div>
    </div>
  )
}
