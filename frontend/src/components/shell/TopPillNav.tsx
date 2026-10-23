import { motion } from 'framer-motion'
import { Icon } from '../Icon'
import { NAV_ITEMS } from '../../data'
import type { Mode, NavId } from '../../types'

interface TopPillNavProps {
  mode: Mode
  activeTab: NavId
  onTabChange: (id: NavId) => void
  onModeSwitch: () => void
  notificationCount?: number
}

export function TopPillNav({
  mode,
  activeTab,
  onTabChange,
  onModeSwitch,
  notificationCount = 3,
}: TopPillNavProps) {
  return (
    <header className="topbar">
      <div className="brand-lockup">
        <motion.div
          className="brand-mark"
          whileHover={{ rotate: 0, scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          <Icon name="spark" size={20} />
        </motion.div>
        <div className="brand-copy">
          <strong>Vigilio</strong>
          <span>Autonomous Logistics Network</span>
        </div>
      </div>

      <nav className="top-nav" aria-label="Primary navigation">
        {NAV_ITEMS.map((item) => {
          const isActive = activeTab === item.id && mode === 'live'
          return (
            <button
              key={item.id}
              className={`nav-tab ${isActive ? 'is-active' : ''}`}
              onClick={() => onTabChange(item.id)}
              style={{ position: 'relative' }}
            >
              <Icon name={item.icon} size={15} />
              <span>{item.label}</span>
              {isActive && (
                <motion.div
                  layoutId="activeTabIndicator"
                  style={{
                    position: 'absolute',
                    inset: 0,
                    borderRadius: 999,
                    backgroundColor: '#1b1b20',
                    zIndex: -1,
                  }}
                  transition={{ type: 'spring', stiffness: 380, damping: 30 }}
                />
              )}
            </button>
          )
        })}
        <button
          className={`nav-tab ${mode === 'chaos' ? 'is-active' : ''}`}
          onClick={onModeSwitch}
          style={{ position: 'relative' }}
        >
          <Icon name="flame" size={15} />
          <span>Chaos Lab</span>
          {mode === 'chaos' && (
            <motion.div
              layoutId="activeTabIndicator"
              style={{
                position: 'absolute',
                inset: 0,
                borderRadius: 999,
                backgroundColor: '#e64a20',
                zIndex: -1,
              }}
              transition={{ type: 'spring', stiffness: 380, damping: 30 }}
            />
          )}
        </button>
      </nav>

      <div className="top-actions">
        <button className="icon-button quiet" aria-label="Search">
          <Icon name="search" size={17} />
        </button>
        <button className="icon-button quiet notification-button" aria-label="Open alerts">
          <Icon name="bell" size={17} />
          {notificationCount > 0 && <span className="notification-dot" />}
        </button>
        <div className="user-chip">
          <div className="avatar">VG</div>
          <div>
            <strong>HQ Ops</strong>
            <span>Active Coordinator</span>
          </div>
          <Icon name="chevron" size={14} />
        </div>
      </div>
    </header>
  )
}
