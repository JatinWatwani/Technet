import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { Icon } from '../../components/Icon'
import { Shelter } from '../../api/client'

interface MobileSheltersDirectoryViewProps {
  shelters: Shelter[]
  onSelectShelter?: (shelter: Shelter) => void
  onNavigateToShelter?: (shelter: Shelter) => void
}

export function MobileSheltersDirectoryView({
  shelters,
  onSelectShelter,
  onNavigateToShelter,
}: MobileSheltersDirectoryViewProps) {
  const [filter, setFilter] = useState<'all' | 'open' | 'critical'>('all')

  const filteredShelters = shelters.filter((s) => {
    if (filter === 'open') return s.open && s.status !== 'OVER_CAPACITY'
    if (filter === 'critical') return s.status === 'OVER_CAPACITY' || !s.open
    return true
  })

  return (
    <div className="mobile-view-content mobile-shelters-view">
      {/* 1. Header */}
      <div className="mobile-section-header">
        <div>
          <span className="mobile-eyebrow">RECEIVING NETWORK RADAR</span>
          <h2 className="mobile-title">Relief Camps & Hubs</h2>
        </div>
      </div>

      {/* 2. Filter Tabs */}
      <div className="mobile-filter-pills">
        <button
          className={`filter-pill ${filter === 'all' ? 'is-active' : ''}`}
          onClick={() => setFilter('all')}
        >
          All Camps ({shelters.length})
        </button>
        <button
          className={`filter-pill ${filter === 'open' ? 'is-active' : ''}`}
          onClick={() => setFilter('open')}
        >
          Open for Intake
        </button>
        <button
          className={`filter-pill ${filter === 'critical' ? 'is-active' : ''}`}
          onClick={() => setFilter('critical')}
        >
          Overcapacity / Capped
        </button>
      </div>

      {/* 3. Camps List */}
      <div className="mobile-camps-stack">
        {filteredShelters.map((shelter) => {
          const isOvercapacity = shelter.status === 'OVER_CAPACITY' || !shelter.open
          const currentDemand = shelter.demand_remaining
          const openSlots = shelter.receiving_capacity_remaining

          return (
            <motion.div
              key={shelter.id}
              className={`mobile-camp-card ${isOvercapacity ? 'is-overcapacity' : 'is-healthy'}`}
              whileTap={{ scale: 0.98 }}
              onClick={() => onSelectShelter?.(shelter)}
            >
              <div className="camp-card-top">
                <div className="camp-title-col">
                  <strong className="camp-name">{shelter.name}</strong>
                  <span className="camp-status-badge">
                    {isOvercapacity ? '⛔ OVERCAPACITY · CLOSED' : '✓ INTAKE NOMINAL'}
                  </span>
                </div>
                <div className="camp-distance-chip">
                  {isOvercapacity ? '⚠️ Bypass' : '1.4 km'}
                </div>
              </div>

              {/* Capacity Bar */}
              <div className="camp-capacity-section">
                <div className="capacity-labels-row">
                  <span>Capacity Intake</span>
                  <strong>{isOvercapacity ? '50 / 50 (100% Capped)' : `${currentDemand} occupied · ${openSlots} available`}</strong>
                </div>
                <div className="mobile-capacity-bar-track">
                  <div
                    className={`mobile-capacity-bar-fill ${isOvercapacity ? 'fill-red' : 'fill-green'}`}
                    style={{ width: isOvercapacity ? '100%' : '32%' }}
                  />
                </div>
              </div>

              {/* Navigation CTA */}
              <div className="camp-card-actions">
                {isOvercapacity ? (
                  <div className="camp-divert-banner">
                    <span>Automated Divert to Relief Camp B Active</span>
                  </div>
                ) : (
                  <button
                    className="camp-navigate-btn"
                    onClick={(e) => {
                      e.stopPropagation()
                      onNavigateToShelter?.(shelter)
                    }}
                  >
                    <Icon name="arrowRight" size={14} />
                    <span>Navigate to {shelter.name.split('(')[0]}</span>
                  </button>
                )}
              </div>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}
