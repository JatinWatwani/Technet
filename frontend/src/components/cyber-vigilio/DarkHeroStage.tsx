import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Icon } from '../Icon'
import { CyberOrbitalHud } from './CyberOrbitalHud'
import { CyberLiveFeed } from './CyberLiveFeed'
import { Incident } from '../../api/client'

interface DarkHeroStageProps {
  onBackToOverview?: () => void
  onTriggerReroute?: () => void
  shelterAOverflow?: boolean
  isRerouting?: boolean
  rerouteResolved?: boolean
  onResolveIncident?: (id: string) => void
  onSelectSeverity?: (sev: string) => void
  onOpenMap?: () => void
  incidents?: Incident[]
}

export function DarkHeroStage({
  onBackToOverview,
  onTriggerReroute,
  shelterAOverflow = true,
  isRerouting = false,
  rerouteResolved = false,
  onResolveIncident,
  onSelectSeverity,
  onOpenMap,
  incidents,
}: DarkHeroStageProps) {
  const [selectedSev, setSelectedSev] = useState<string>('all')
  const [isCollapsed, setIsCollapsed] = useState<boolean>(false)
  const [isViewMenuOpen, setIsViewMenuOpen] = useState<boolean>(false)

  const SEVERITY_BADGES = incidents && incidents.length > 0 ? [
    { label: 'C', count: incidents.filter((i) => i.severity === 'CRITICAL' && i.status !== 'RESOLVED').length, name: 'Critical' },
    { label: 'H', count: incidents.filter((i) => i.severity === 'HIGH' && i.status !== 'RESOLVED').length, name: 'High' },
    { label: 'M', count: incidents.filter((i) => i.severity === 'MEDIUM' && i.status !== 'RESOLVED').length, name: 'Medium' },
    { label: 'L', count: incidents.filter((i) => i.severity === 'LOW' && i.status !== 'RESOLVED').length, name: 'Low' },
  ] : [
    { label: 'C', count: 3, name: 'Critical' },
    { label: 'H', count: 2, name: 'High' },
    { label: 'M', count: 5, name: 'Medium' },
    { label: 'L', count: 0, name: 'Low' },
  ]

  const handleSevClick = (sev: string) => {
    const next = selectedSev === sev ? 'all' : sev
    setSelectedSev(next)
    onSelectSeverity?.(next)
  }

  const toggleCollapse = () => {
    setIsCollapsed((prev) => !prev)
  }

  if (isCollapsed) {
    return (
      <section
        className="cyber-dark-stage is-collapsed-stage"
        onClick={toggleCollapse}
        title="Click to expand full Dynamic View Dial HUD"
      >
        <div className="collapsed-left-col">
          <button
            className="stage-back-btn"
            onClick={(e) => {
              e.stopPropagation()
              toggleCollapse()
            }}
            title="Expand Dynamic View"
          >
            <motion.span
              animate={{ rotate: -90 }}
              transition={{ duration: 0.2 }}
              style={{ display: 'grid', placeItems: 'center' }}
            >
              <Icon name="arrowDown" size={13} />
            </motion.span>
            <span>Dynamic View (Dial HUD Minimized)</span>
          </button>
        </div>

        <div className="collapsed-chips-row">
          <div className="collapsed-chip">
            <span className="chip-muted">Data Ingestion:</span>
            <strong>65 Total</strong>
          </div>
          <span className="collapsed-dot">•</span>
          <div className="collapsed-chip">
            <span className="chip-muted">Resolution:</span>
            <strong className="text-green">{rerouteResolved ? '98% Autonomous' : '10% Manual'}</strong>
          </div>
          <span className="collapsed-dot">•</span>
          <div className="collapsed-chip">
            <span className="chip-muted">Active Alerts:</span>
            <strong className="text-orange">{rerouteResolved ? '0 Breaches' : '3 Critical (Shelter A Overflow)'}</strong>
          </div>
          <span className="collapsed-dot">•</span>
          <div className="collapsed-chip">
            <span className="chip-muted">Couriers:</span>
            <strong>3 Live GPS Verified</strong>
          </div>
        </div>

        <div className="collapsed-right-col">
          <button
            className="collapsed-expand-btn"
            onClick={(e) => {
              e.stopPropagation()
              toggleCollapse()
            }}
          >
            <span>Expand Dial HUD</span>
            <Icon name="chevron" size={13} />
          </button>
        </div>
      </section>
    )
  }

  return (
    <section className="cyber-dark-stage">
      {/* Left Column: Metrics & Ingestion */}
      <div className="stage-left-col">
        {/* Header Breadcrumb with <- Dynamic View matching reference screenshot */}
        <div className="dynamic-view-dropdown-wrap" style={{ position: 'relative' }}>
          <button
            className="stage-back-btn"
            onClick={toggleCollapse}
            title="Click to collapse Dynamic View dial stage"
          >
            <motion.span
              animate={{ x: [0, -3, 0] }}
              transition={{ repeat: Infinity, duration: 2, ease: 'easeInOut' }}
              style={{ display: 'grid', placeItems: 'center' }}
            >
              <Icon name="arrowDown" size={13} />
            </motion.span>
            <span>← Dynamic View</span>
          </button>
        </div>

        {/* Data Ingestion Card */}
        <div className="ingestion-metric-box">
          <span className="metric-eyebrow">Data Ingestion</span>
          <div className="ingestion-value-row">
            <span className="big-ingest-number">65</span>
            <span className="ingest-unit">Total</span>
          </div>

          {/* Sparkline SVG */}
          <div className="sparkline-wrap">
            <svg
              className="sparkline-svg"
              viewBox="0 0 160 50"
              preserveAspectRatio="none"
            >
              <defs>
                <linearGradient id="spark-grad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#ffffff" stopOpacity="0.4" />
                  <stop offset="100%" stopColor="#ffffff" stopOpacity="0.0" />
                </linearGradient>
              </defs>
              <path
                d="M 0 38 Q 20 40 40 28 T 80 18 T 120 32 T 160 12 L 160 50 L 0 50 Z"
                fill="url(#spark-grad)"
              />
              <path
                d="M 0 38 Q 20 40 40 28 T 80 18 T 120 32 T 160 12"
                fill="none"
                stroke="#ffffff"
                strokeWidth="2.2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <circle cx="160" cy="12" r="3.5" fill="#18B880" />
            </svg>
          </div>
        </div>

        {/* Open Incidents Badges */}
        <div className="open-incidents-box">
          <span className="metric-eyebrow">Open Incidents</span>
          <div className="incident-pills-row">
            {SEVERITY_BADGES.map((b) => {
              const isSelected = selectedSev === b.label
              return (
                <button
                  key={b.label}
                  className={`sev-badge-btn ${isSelected ? 'is-selected' : ''}`}
                  onClick={() => handleSevClick(b.label)}
                  title={`${b.name}: ${b.count} open`}
                >
                  <span className="sev-dot">{b.count}</span>
                  <span className="sev-letter">{b.label}</span>
                </button>
              )
            })}
          </div>
        </div>
      </div>

      {/* Center Column: The Orbital Radar HUD */}
      <div className="stage-center-col">
        <CyberOrbitalHud
          onTriggerReroute={onTriggerReroute}
          isRerouting={isRerouting}
          rerouteResolved={rerouteResolved}
        />
      </div>

      {/* Right Column: Live Incident Feed */}
      <div className="stage-right-col">
        <CyberLiveFeed
          shelterAOverflow={shelterAOverflow}
          rerouteResolved={rerouteResolved}
          onTriggerReroute={onTriggerReroute}
          onResolveIncident={onResolveIncident}
          backendIncidents={incidents}
        />
      </div>
    </section>
  )
}
