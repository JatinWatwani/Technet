import { Icon } from '../Icon'
import type { Incident } from '../../api/client'

interface AlertsBentoCardProps {
  waterOnline: boolean
  onToggleWater: () => void
  onOpenAlertsTable: () => void
  incidents?: Incident[]
}

export function AlertsBentoCard({
  waterOnline,
  onToggleWater,
  onOpenAlertsTable,
  incidents = [],
}: AlertsBentoCardProps) {
  const highCount = incidents.filter((i) => i.severity === 'HIGH' || i.severity === 'CRITICAL').length
  const medCount = incidents.filter((i) => i.severity === 'MEDIUM').length
  const lowCount = incidents.filter((i) => i.severity === 'LOW').length
  const activeCount = incidents.filter((i) => i.status !== 'RESOLVED').length

  const ALERT_LEVELS = [
    { label: 'Critical / High', color: '#CE6969', value: incidents.length > 0 ? highCount : 3, countSegments: 18, filledSegments: Math.min(18, highCount * 3 || 6) },
    { label: 'Medium', color: '#F9771D', value: incidents.length > 0 ? medCount : 5, countSegments: 18, filledSegments: Math.min(18, medCount * 2 || 4) },
    { label: 'Low', color: '#18B880', value: incidents.length > 0 ? lowCount : 1, countSegments: 18, filledSegments: Math.min(18, lowCount || 2) },
    { label: 'Active Alerts', color: '#CE6969', value: incidents.length > 0 ? activeCount : 3, countSegments: 18, filledSegments: Math.min(18, activeCount * 3 || 6) },
  ]

  return (
    <div className="cyber-bento-card card-alerts">
      {/* Card Header */}
      <div className="card-header-row">
        <h3>Alerts</h3>
        <button
          className="card-arrow-btn"
          onClick={onOpenAlertsTable}
          title="Open Complete Alerts Breakdown"
          aria-label="View alerts table"
        >
          <Icon name="arrowUp" size={13} />
        </button>
      </div>

      {/* Segmented Dashed Bars */}
      <div className="alerts-bars-stack">
        {ALERT_LEVELS.map((level) => (
          <div key={level.label} className="alert-bar-row">
            <span className="alert-level-label">{level.label}</span>

            {/* Segmented Dashed Track */}
            <div className="segmented-track">
              {Array.from({ length: level.countSegments }).map((_, i) => {
                const isFilled = i < level.filledSegments
                return (
                  <span
                    key={i}
                    className="track-segment"
                    style={{
                      backgroundColor: isFilled ? level.color : 'rgba(27, 26, 38, 0.08)',
                    }}
                  />
                )
              })}
            </div>

            <span className="alert-count-val">{level.value}</span>
          </div>
        ))}
      </div>

      {/* Scenario 4 Dependency Switcher */}
      <div className={`alerts-footer-guard ${waterOnline ? '' : 'is-blocked'}`}>
        <div className="guard-info">
          <Icon name={waterOnline ? 'water' : 'alert'} size={14} />
          <span>
            {waterOnline
              ? 'Clean water prerequisite verified'
              : 'Shelter C water blocked · Raw rations rerouted'}
          </span>
        </div>
        <button
          className="guard-toggle-btn"
          onClick={onToggleWater}
          title="Toggle Shelter C clean water prerequisite (Scenario 4)"
        >
          {waterOnline ? 'ON' : 'OFF'}
        </button>
      </div>
    </div>
  )
}
