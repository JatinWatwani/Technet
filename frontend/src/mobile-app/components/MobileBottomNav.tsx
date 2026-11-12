import React from 'react'
import { motion } from 'framer-motion'
import { Icon } from '../../components/Icon'
import type { IconName } from '../../types'

export type MobileTabId = 'dispatch' | 'active' | 'scan' | 'shelters' | 'profile'

interface MobileBottomNavProps {
  activeTab: MobileTabId
  onTabChange: (tab: MobileTabId) => void
  hasActiveTrip?: boolean
  availableCount?: number
}

export function MobileBottomNav({
  activeTab,
  onTabChange,
  hasActiveTrip = true,
  availableCount = 3,
}: MobileBottomNavProps) {
  const TABS: { id: MobileTabId; label: string; icon: IconName; badge?: number | string }[] = [
    { id: 'dispatch', label: 'Offers', icon: 'box', badge: availableCount },
    { id: 'active', label: 'Active Run', icon: 'bike', badge: hasActiveTrip ? 'LIVE' : undefined },
    { id: 'scan', label: 'Scan QR', icon: 'shield' },
    { id: 'shelters', label: 'Camps', icon: 'home' },
    { id: 'profile', label: 'Impact', icon: 'layers' },
  ]

  return (
    <nav className="mobile-bottom-navbar" aria-label="Mobile Navigation">
      {TABS.map((tab) => {
        const isActive = activeTab === tab.id
        return (
          <button
            key={tab.id}
            className={`mobile-tab-item ${isActive ? 'is-active' : ''}`}
            onClick={() => onTabChange(tab.id)}
          >
            <div className="mobile-tab-icon-wrap">
              <Icon name={tab.icon} size={20} />
              {tab.badge && (
                <span className={`mobile-tab-badge ${tab.badge === 'LIVE' ? 'badge-pulse' : ''}`}>
                  {tab.badge}
                </span>
              )}
              {isActive && (
                <motion.div
                  layoutId="mobileActiveIndicator"
                  className="mobile-tab-indicator-glow"
                  transition={{ type: 'spring', stiffness: 500, damping: 35 }}
                />
              )}
            </div>
            <span className="mobile-tab-label">{tab.label}</span>
          </button>
        )
      })}
    </nav>
  )
}
