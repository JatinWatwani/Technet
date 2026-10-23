import { motion } from 'framer-motion'
import { Icon } from '../Icon'

export function DedicatedMapView() {
  return (
    <div className="dedicated-map-view">
      <div className="map-view-header">
        <div>
          <h2>Autonomous Last-Mile Network Graph</h2>
          <p>Real-time vector topology showing active riders, donor hubs, and capacity-aware shelter receivers.</p>
        </div>
        <div className="map-view-stats">
          <div className="stat-pill">
            <span className="live-pulse" />
            <strong>12</strong> Riders en route
          </div>
          <div className="stat-pill orange">
            <Icon name="route" size={14} />
            <strong>3</strong> Dynamic Reroutes
          </div>
          <div className="stat-pill mint">
            <Icon name="check" size={14} />
            <strong>100%</strong> Custody verified
          </div>
        </div>
      </div>

      <div className="fullscreen-map-canvas">
        <div className="map-grid-lines" />
        <svg
          viewBox="0 0 1000 480"
          preserveAspectRatio="none"
          role="img"
          aria-label="Expanded full-canvas last-mile route map"
        >
          {/* Major arterial roads */}
          <path
            d="M60 380 C180 340 140 220 280 200 S420 340 540 260 S660 140 780 180 S900 280 980 120"
            className="map-road"
            style={{ strokeWidth: 16 }}
          />
          <path
            d="M100 120 C220 200 300 60 420 140 S580 380 700 300 S820 140 940 320"
            className="map-road muted"
            style={{ strokeWidth: 10 }}
          />

          {/* Active routes */}
          <motion.path
            d="M180 320 C300 260 380 300 500 260 S720 180 840 150"
            className="map-route"
            style={{ strokeWidth: 4 }}
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 1.2, ease: 'easeInOut' }}
          />
          {/* Reroute arc */}
          <motion.path
            d="M500 260 C600 200 680 200 800 310"
            className="map-route secondary"
            style={{ strokeWidth: 4, strokeDasharray: '8 6' }}
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 1.4, delay: 0.3, ease: 'easeInOut' }}
          />

          {/* Nodes */}
          <circle cx="180" cy="320" r="14" className="map-node donor" />
          <circle cx="500" cy="260" r="14" className="map-node rider" />
          <circle cx="840" cy="150" r="18" className="map-node shelter" />
          <circle cx="800" cy="310" r="18" className="map-node shelter light" />

          {/* Radar pulses */}
          <circle cx="180" cy="320" r="28" className="map-pulse" />
          <circle cx="500" cy="260" r="24" className="map-pulse orange-pulse" />
          <circle cx="840" cy="150" r="32" className="map-pulse" />
          <circle cx="800" cy="310" r="30" className="map-pulse orange-pulse" />
        </svg>

        <div className="map-label donor-label" style={{ left: '16%', bottom: '33%' }}>
          <span />
          <strong>Donor Hub A</strong> (Banquet Hall · 180 Meals Ready)
        </div>
        <div className="map-label rider-label" style={{ left: '48%', top: '51%' }}>
          <span />
          <strong>Rider #07</strong> (Physical Custody · 40 Meals)
        </div>
        <div className="map-label shelter-label" style={{ right: '14%', top: '27%' }}>
          <span />
          <strong>Shelter A</strong> (At Capacity · 50/50 Full)
        </div>
        <div className="map-label shelter-label" style={{ right: '18%', bottom: '28%' }}>
          <span style={{ background: '#e85322' }} />
          <strong>Shelter B</strong> (Verified Fallback · 120 Meals Needed)
        </div>
      </div>
    </div>
  )
}
