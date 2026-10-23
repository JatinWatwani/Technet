import { motion } from 'framer-motion'
import { Icon } from '../Icon'

interface CyberTopNavProps {
  activeTab: string
  onTabChange: (tab: string) => void
  onOpenAlertsTable: () => void
  onOpenCreateModal: () => void
  onOpenFilterDrawer: () => void
  onToggleOperationsMatrix: () => void
  onOpenSettingsModal: () => void
  theme: 'light' | 'dark'
  onToggleTheme: () => void
  isMatrixActive?: boolean
}

const TABS = [
  { id: 'landing', label: 'Landing Page' },
  { id: 'overview', label: 'Data overview' },
  { id: 'map', label: 'Live Map ↗' },
  { id: 'alerts', label: 'Key Alerts' },
  { id: 'insights', label: 'Insights' },
  { id: 'executions', label: 'Executions' },
]

export function CyberTopNav({
  activeTab,
  onTabChange,
  onOpenAlertsTable,
  onOpenCreateModal,
  onOpenFilterDrawer,
  onToggleOperationsMatrix,
  onOpenSettingsModal,
  theme,
  onToggleTheme,
  isMatrixActive = false,
}: CyberTopNavProps) {
  return (
    <header className="cyber-topbar">
      {/* Brand */}
      <div className="cyber-brand" onClick={() => onTabChange('overview')} style={{ cursor: 'pointer' }}>
        <motion.div
          className="cyber-logo-mark"
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
            <path
              d="M12 2L4 6V12C4 17.5 7.4 22.6 12 24C16.6 22.6 20 17.5 20 12V6L12 2Z"
              stroke="#F9771D"
              strokeWidth="2.4"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <circle cx="12" cy="12" r="3" fill="#F9771D" />
          </svg>
        </motion.div>
        <span className="cyber-brand-name">
          Vigilio<span className="cyber-brand-dot">.</span>
        </span>
      </div>

      {/* Tabs */}
      <nav className="cyber-tabs" aria-label="Operational views">
        {TABS.map((tab) => {
          const isActive = activeTab === tab.id
          return (
            <button
              key={tab.id}
              className={`cyber-tab-btn ${isActive ? 'is-active' : ''}`}
              onClick={() => onTabChange(tab.id)}
            >
              <span>{tab.label}</span>
              {isActive && (
                <motion.div
                  layoutId="cyberActiveTab"
                  className="cyber-tab-indicator"
                  transition={{ type: 'spring', stiffness: 450, damping: 32 }}
                />
              )}
            </button>
          )
        })}
        <button
          className="cyber-tab-add"
          onClick={onOpenCreateModal}
          title="Add New Consignment or Target"
          aria-label="Add target"
        >
          <Icon name="plus" size={14} />
        </button>
      </nav>

      {/* Utilities */}
      <div className="cyber-top-actions">
        {/* 1. Alerts Table Button */}
        <button
          className="cyber-table-btn"
          onClick={onOpenAlertsTable}
          title="Open Master Alerts Ledger Table"
        >
          <Icon name="layers" size={14} />
          <span>Alerts Table</span>
        </button>

        {/* 2. Parameters & Filter Drawer Button (Sliders icon) */}
        <button
          className="cyber-icon-btn"
          onClick={onOpenFilterDrawer}
          title="Telemetry Thresholds & Filter Parameters"
          aria-label="Filter parameters"
        >
          <Icon name="settings" size={15} />
        </button>

        {/* 3. High-Density Grid Matrix Button (Grid icon) */}
        <button
          className={`cyber-icon-btn ${isMatrixActive ? 'is-active-btn' : ''}`}
          onClick={onToggleOperationsMatrix}
          title={isMatrixActive ? 'Return to Standard Dashboard' : 'Open Operations Command Grid'}
          aria-label="Operations grid"
        >
          <Icon name="grid" size={15} />
        </button>

        {/* 4. System Settings & Node Config Button */}
        <button
          className="cyber-icon-btn"
          onClick={onOpenSettingsModal}
          title="System Settings, Clock Speed & Forensic Audit"
          aria-label="System settings"
        >
          <Icon name="command" size={15} />
        </button>

        {/* 5. Light and Dark Mode Toggle Button (Replaces the download button) */}
        <button
          className="cyber-icon-btn theme-toggle-btn"
          onClick={onToggleTheme}
          title={theme === 'dark' ? 'Switch to Pale Ecru Sage Light Mode' : 'Switch to Obsidian Stealth Dark Mode'}
          aria-label="Toggle theme mode"
        >
          <motion.div
            key={theme}
            initial={{ rotate: -120, scale: 0.5, opacity: 0 }}
            animate={{ rotate: 0, scale: 1, opacity: 1 }}
            exit={{ rotate: 120, scale: 0.5, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 400, damping: 22 }}
            style={{ display: 'grid', placeItems: 'center' }}
          >
            <Icon name={theme === 'dark' ? 'sun' : 'moon'} size={15} />
          </motion.div>
        </button>
      </div>
    </header>
  )
}
