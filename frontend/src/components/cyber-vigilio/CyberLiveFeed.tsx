import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Icon } from '../Icon'
import { Incident } from '../../api/client'

export interface IncidentItem {
  id: string
  title: string
  subtext: string
  isOrangeHero?: boolean
  badge?: string
  timeAgo: string
  status: 'critical' | 'high' | 'normal' | 'resolved'
  actionText?: string
  timeWindowHours: number
}

interface CyberLiveFeedProps {
  onResolveIncident?: (id: string) => void
  onTriggerReroute?: () => void
  shelterAOverflow?: boolean
  rerouteResolved?: boolean
  backendIncidents?: Incident[]
}

export function CyberLiveFeed({
  onResolveIncident,
  onTriggerReroute,
  shelterAOverflow = true,
  rerouteResolved = false,
  backendIncidents,
}: CyberLiveFeedProps) {
  const [timeFilter, setTimeFilter] = useState<'24h' | '1h' | '7d'>('24h')
  const [showFilterDropdown, setShowFilterDropdown] = useState(false)
  const [showMoreMenu, setShowMoreMenu] = useState(false)
  const [criticalOnly, setCriticalOnly] = useState(false)
  const [selectedIncident, setSelectedIncident] = useState<IncidentItem | null>(null)

  const liveMappedIncidents: IncidentItem[] = (backendIncidents && backendIncidents.length > 0)
    ? backendIncidents.map((inc) => ({
        id: inc.id,
        title: inc.reason_code ? inc.reason_code.replace(/_/g, ' ') : 'Sentinel Anomaly',
        subtext: inc.description || 'Autonomous sentinel verification event',
        isOrangeHero: inc.severity === 'CRITICAL' && inc.status !== 'RESOLVED',
        badge: inc.severity === 'CRITICAL' ? 'C' : inc.severity === 'HIGH' ? 'H' : 'M',
        timeAgo: 'Live',
        status: inc.status === 'RESOLVED' ? 'resolved' : (inc.severity.toLowerCase() as any),
        actionText: inc.status === 'RESOLVED' ? 'Verified' : 'Resolve',
        timeWindowHours: 1,
      }))
    : []

  const rawIncidents: IncidentItem[] = liveMappedIncidents.length > 0 ? liveMappedIncidents : [
    {
      id: 'inc-1',
      title: '3 Reassignments completed',
      subtext: 'Unpicked parcels dynamically reallocated to backup pool',
      badge: 'C',
      timeAgo: '4m ago',
      status: 'critical',
      timeWindowHours: 1,
    },
    {
      id: 'inc-2',
      title: rerouteResolved
        ? 'Shelter A Overflow Resolved'
        : 'Shelter A | Capacity Overflow (50/50)',
      subtext: rerouteResolved
        ? 'Rider #07 successfully delivered 40 meals to Relief Camp B inside 19m buffer'
        : 'Rider #07 has physical custody (40 meals) · Shelter B fallback ready',
      isOrangeHero: !rerouteResolved && shelterAOverflow,
      badge: rerouteResolved ? '✓' : 'ALERT',
      timeAgo: rerouteResolved ? 'Just now' : '12m ago',
      status: rerouteResolved ? 'resolved' : 'high',
      actionText: rerouteResolved ? 'View Solver Proof' : 'Verify Reroute',
      timeWindowHours: 1,
    },
    {
      id: 'inc-3',
      title: '2 Lease timers expired',
      subtext: 'Rider #12 volunteer stall confirmed · Zero inventory loss',
      badge: 'M',
      timeAgo: '18m ago',
      status: 'high',
      timeWindowHours: 24,
    },
    {
      id: 'inc-4',
      title: 'Batch split committed | ID-997',
      subtext: '180 portions split across 5 sub-tickets · 0 unaccounted',
      badge: 'L',
      timeAgo: '24m ago',
      status: 'normal',
      timeWindowHours: 24,
    },
    {
      id: 'inc-5',
      title: 'Cold-chain telemetry heartbeat check',
      subtext: 'City Pharmacy 24 insulin units within safe 3.8°C range',
      badge: 'H',
      timeAgo: '2h ago',
      status: 'critical',
      timeWindowHours: 24,
    },
    {
      id: 'inc-6',
      title: 'Historical baseline sync | Cluster 04',
      subtext: '12 active riders verified against spatial demand matrix',
      badge: 'L',
      timeAgo: '3d ago',
      status: 'normal',
      timeWindowHours: 168,
    },
  ]

  // Filter based on selected time window and critical toggle
  const maxHours = timeFilter === '1h' ? 1 : timeFilter === '24h' ? 24 : 168
  const filteredIncidents = rawIncidents.filter((inc) => {
    if (criticalOnly && inc.status !== 'critical' && inc.status !== 'high') {
      return false
    }
    return inc.timeWindowHours <= maxHours
  })

  const handleCardClick = (item: IncidentItem) => {
    setSelectedIncident(item)
  }

  const handleHeroAction = (e: React.MouseEvent) => {
    e.stopPropagation()
    onTriggerReroute?.()
  }

  return (
    <div className="cyber-live-feed-panel">
      {/* Feed Header */}
      <div className="feed-header">
        <div className="feed-title-block">
          <span className="live-emerald-pulse" />
          <span className="feed-title">Live Feed</span>
          {criticalOnly && <span className="critical-filter-tag">Critical Only</span>}
        </div>

        <div className="feed-controls" style={{ position: 'relative' }}>
          {/* Time Filter Pill with functional dropdown */}
          <button
            className="feed-filter-pill"
            onClick={() => setShowFilterDropdown((prev) => !prev)}
            title="Select time window"
          >
            <span>{timeFilter}</span>
            <Icon name="chevron" size={11} />
          </button>

          <AnimatePresence>
            {showFilterDropdown && (
              <motion.div
                className="feed-dropdown-menu"
                initial={{ opacity: 0, y: 5 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 5 }}
              >
                {(['1h', '24h', '7d'] as const).map((t) => (
                  <button
                    key={t}
                    className={`dropdown-item ${timeFilter === t ? 'is-active' : ''}`}
                    onClick={() => {
                      setTimeFilter(t)
                      setShowFilterDropdown(false)
                    }}
                  >
                    <span>{t === '1h' ? 'Last 1 Hour' : t === '24h' ? 'Last 24 Hours' : 'Last 7 Days'}</span>
                  </button>
                ))}
              </motion.div>
            )}
          </AnimatePresence>

          {/* More Options Menu */}
          <button
            className="feed-more-btn"
            onClick={() => setShowMoreMenu((prev) => !prev)}
            aria-label="Feed filter options"
          >
            <Icon name="more" size={14} />
          </button>

          <AnimatePresence>
            {showMoreMenu && (
              <motion.div
                className="feed-dropdown-menu more-menu"
                initial={{ opacity: 0, y: 5 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 5 }}
              >
                <button
                  className="dropdown-item"
                  onClick={() => {
                    setCriticalOnly((prev) => !prev)
                    setShowMoreMenu(false)
                  }}
                >
                  <span>{criticalOnly ? 'Show All Severity' : 'Filter Critical Only'}</span>
                </button>
                <button
                  className="dropdown-item"
                  onClick={() => {
                    onTriggerReroute?.()
                    setShowMoreMenu(false)
                  }}
                >
                  <span>Reroute Shelter A Cargo</span>
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Feed Stack */}
      <div className="feed-stack">
        {filteredIncidents.map((item, index) => {
          if (item.isOrangeHero) {
            return (
              <motion.div
                key={item.id}
                className="feed-card-hero-orange"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.35, delay: index * 0.04 }}
                onClick={() => handleCardClick(item)}
              >
                <div className="hero-top-row">
                  <div className="hero-badge-wrap">
                    <span className="hero-alert-icon">
                      <Icon name="alert" size={14} />
                    </span>
                    <strong>{item.title}</strong>
                  </div>
                  <span className="hero-time">{item.timeAgo}</span>
                </div>
                <p className="hero-subtext">{item.subtext}</p>
                {item.actionText && (
                  <button className="hero-action-pill" onClick={handleHeroAction}>
                    <Icon name="zap" size={12} />
                    <span>{item.actionText}</span>
                  </button>
                )}
              </motion.div>
            )
          }

          if (item.status === 'resolved') {
            return (
              <motion.div
                key={item.id}
                className="feed-card-resolved-green"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                onClick={() => handleCardClick(item)}
              >
                <div className="hero-top-row">
                  <div className="hero-badge-wrap">
                    <span className="resolved-check-icon">
                      <Icon name="check" size={14} />
                    </span>
                    <strong>{item.title}</strong>
                  </div>
                  <span className="hero-time">{item.timeAgo}</span>
                </div>
                <p className="hero-subtext">{item.subtext}</p>
              </motion.div>
            )
          }

          return (
            <motion.div
              key={item.id}
              className="feed-card-item"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: index * 0.04 }}
              onClick={() => handleCardClick(item)}
            >
              <div className="feed-item-top">
                <span className={`feed-badge ${item.status}`}>
                  {item.badge}
                </span>
                <span className="feed-item-title">{item.title}</span>
                <span className="feed-time">{item.timeAgo}</span>
              </div>
              <p className="feed-item-subtext">{item.subtext}</p>
            </motion.div>
          )
        })}
      </div>

      {/* Incident Detail / Resolution Popover */}
      <AnimatePresence>
        {selectedIncident && (
          <motion.div
            className="incident-detail-overlay"
            initial={{ opacity: 0, y: 12, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 12, scale: 0.97 }}
            transition={{ duration: 0.2 }}
          >
            <div className="detail-header">
              <div className="detail-title-row">
                <span className={`detail-pill ${selectedIncident.status}`}>
                  {selectedIncident.status.toUpperCase()}
                </span>
                <h4 className="detail-title-text" title={selectedIncident.title}>
                  {selectedIncident.title}
                </h4>
              </div>
              <button
                className="popover-close"
                onClick={() => setSelectedIncident(null)}
                aria-label="Close incident inspection"
              >
                <Icon name="x" size={13} />
              </button>
            </div>

            <div className="detail-meta-row">
              <span className="detail-timestamp">Logged {selectedIncident.timeAgo}</span>
              <span className="detail-meta-dot">•</span>
              <span className="detail-window">Window &lt;{selectedIncident.timeWindowHours}h</span>
              <span className="detail-meta-dot">•</span>
              <span className="detail-verification">ID: {selectedIncident.id.toUpperCase()}</span>
            </div>

            <div className="detail-body-card">
              <p className="detail-body">{selectedIncident.subtext}</p>
            </div>

            <div className="detail-actions">
              <button
                className="btn-resolve-direct"
                onClick={() => {
                  onResolveIncident?.(selectedIncident.id)
                  setSelectedIncident(null)
                }}
              >
                <Icon name="check" size={14} />
                <span>Mark Managed</span>
              </button>
              {selectedIncident.id === 'inc-2' && !rerouteResolved && (
                <button
                  className="btn-reroute-direct"
                  onClick={() => {
                    onTriggerReroute?.()
                    setSelectedIncident(null)
                  }}
                >
                  <Icon name="zap" size={14} />
                  <span>Execute Radar Reroute</span>
                </button>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
