import { motion } from 'framer-motion'
import { Icon } from '../Icon'
import type { NavId, IconName } from '../../types'

interface LeftFloatingDockProps {
  activeTab: NavId
  onTabChange: (id: NavId) => void
  isDarkMode?: boolean
  onToggleTheme?: () => void
}

interface DockItem {
  id: NavId
  icon: IconName
  label: string
}

const DOCK_ITEMS: DockItem[] = [
  { id: 'command', icon: 'grid', label: 'Command Center' },
  { id: 'supply', icon: 'box', label: 'Supply Exchange' },
  { id: 'rider', icon: 'bike', label: 'Rider Console' },
  { id: 'shelter', icon: 'home', label: 'Shelter Ops' },
  { id: 'map', icon: 'map', label: 'Live Route Graph' },
  { id: 'library', icon: 'book', label: 'Word / Rule Library' },
]

export function LeftFloatingDock({
  activeTab,
  onTabChange,
  isDarkMode = false,
  onToggleTheme,
}: LeftFloatingDockProps) {
  return (
    <aside className="side-dock">
      <div className="dock-pill">
        {DOCK_ITEMS.map((item) => {
          const isSelected = activeTab === item.id
          return (
            <button
              key={item.id}
              className={`dock-button ${isSelected ? 'is-selected' : ''}`}
              onClick={() => onTabChange(item.id)}
              aria-label={item.label}
              title={item.label}
              style={{ position: 'relative' }}
            >
              <Icon name={item.icon} size={17} />
              {isSelected && (
                <motion.div
                  layoutId="sideDockIndicator"
                  style={{
                    position: 'absolute',
                    inset: 0,
                    borderRadius: '50%',
                    backgroundColor: '#1b1b20',
                    zIndex: -1,
                  }}
                  transition={{ type: 'spring', stiffness: 420, damping: 32 }}
                />
              )}
            </button>
          )
        })}
      </div>

      <div className="dock-pill dock-secondary">
        <button
          className={`dock-button ${!isDarkMode ? 'is-selected' : ''}`}
          onClick={onToggleTheme}
          aria-label="Light / Dark mode toggle"
          title={isDarkMode ? 'Switch to Light Glass' : 'Switch to Dark Onyx'}
        >
          <Icon name="spark" size={16} />
        </button>
        <button className="dock-button" aria-label="Settings" title="Settings">
          <Icon name="settings" size={16} />
        </button>
      </div>

      <div className="dock-status">
        <span className="live-pulse" /> <span>Live</span>
      </div>
    </aside>
  )
}
