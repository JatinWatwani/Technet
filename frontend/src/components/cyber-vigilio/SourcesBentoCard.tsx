import { useState } from 'react'
import { motion } from 'framer-motion'
import { Icon } from '../Icon'
import type { Batch } from '../../api/client'

interface SourcesBentoCardProps {
  onSplitBatch: () => void
  splitComplete: boolean
  batches?: Batch[]
}

export function SourcesBentoCard({ onSplitBatch, splitComplete, batches = [] }: SourcesBentoCardProps) {
  const [activeSlide, setActiveSlide] = useState(0)

  // Use real backend batches if available, otherwise fallback
  const displaySources = batches.length > 0
    ? batches.slice(0, 4).map((b, i) => {
        const accents = ['#6E62D8', '#3999CE', '#329A6E', '#F9771D']
        const icons = ['box', 'shield', 'layers', 'box']
        return {
          id: b.id,
          name: b.item_type.replace(/_/g, ' ').toUpperCase(),
          code: b.id,
          count: b.available_quantity,
          subtext: `${b.item_rules.safe_handling_minutes}m safe window · ${b.item_rules.storage_requirement}`,
          icon: icons[i % icons.length],
          accent: accents[i % accents.length],
        }
      })
    : [
        {
          id: 'cooked',
          name: 'Cooked Meals (Banquet Hall A)',
          code: 'XDR Agent',
          count: 37,
          subtext: '48m safe window · splits across 5 riders',
          icon: 'box',
          accent: '#6E62D8',
        },
        {
          id: 'insulin',
          name: 'Cold-Chain Insulin (Pharmacy)',
          code: 'XDR Analytics BIOS',
          count: 29,
          subtext: 'Cold-chain verified · 2 escort riders',
          icon: 'shield',
          accent: '#3999CE',
        },
        {
          id: 'rations',
          name: 'Raw Ration Kits (Hostel Mess)',
          code: 'XDR BIOS',
          count: 18,
          subtext: 'Needs clean water + cooking fuel',
          icon: 'layers',
          accent: '#329A6E',
        },
      ]

  return (
    <div className="cyber-bento-card card-sources">
      {/* Gentle Peach/Coral Glow Gradient on the right */}
      <div className="card-peach-glow" />

      {/* Card Header */}
      <div className="card-header-row">
        <h3>Sources</h3>
        <button
          className="card-arrow-btn"
          onClick={onSplitBatch}
          title="Trigger 180-Meal Batch Split (Scenario 1)"
          aria-label="Split batch"
        >
          <Icon name="arrowUp" size={13} />
        </button>
      </div>

      {/* Sources List */}
      <div className="sources-list">
        {displaySources.map((s) => (
          <div key={s.id} className="source-row-item">
            <div className="source-left">
              <span className="source-icon-wrap" style={{ color: s.accent }}>
                <Icon name={s.icon as any} size={15} />
              </span>
              <div className="source-text">
                <strong>{s.code}</strong>
                <small>{s.name}</small>
              </div>
            </div>

            <div className="source-right">
              <span className="source-count">{s.count}</span>
              <span className="source-eye" title="Active Real-Time Monitoring">
                <Icon name="target" size={13} />
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Batch Split Trigger & Conservation Proof */}
      <div className="source-action-footer">
        <button
          className={`split-action-btn ${splitComplete ? 'is-complete' : ''}`}
          onClick={onSplitBatch}
        >
          <Icon name={splitComplete ? 'check' : 'plus'} size={13} />
          <span>
            {splitComplete ? '180 = 180 Allocated (Locked)' : '+ Split 180-Meal Batch (Cap 40)'}
          </span>
        </button>

        {/* Carousel Dots */}
        <div className="card-carousel-dots">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className={`carousel-dot ${activeSlide === i ? 'is-active' : ''}`}
              onClick={() => setActiveSlide(i)}
            />
          ))}
        </div>
      </div>
    </div>
  )
}
