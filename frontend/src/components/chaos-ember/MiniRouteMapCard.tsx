import { SectionHeading } from '../common/SectionHeading'

export function MiniRouteMapCard() {
  return (
    <section className="panel map-panel">
      <SectionHeading
        icon="map"
        eyebrow="LIVE ROUTE GRAPH"
        title="Last-mile reroutes"
        action={
          <div className="map-legend">
            <span>
              <i className="legend-dot purple" />
              Active Rider
            </span>
            <span>
              <i className="legend-dot orange" />
              Dynamic Reroute
            </span>
          </div>
        }
      />

      <div className="route-map">
        <div className="map-grid-lines" />
        <svg
          viewBox="0 0 700 270"
          preserveAspectRatio="none"
          role="img"
          aria-label="Stylized live route map with moving riders, donor nodes, and shelter destinations"
        >
          {/* Base Road Network */}
          <path
            d="M52 202 C126 182 94 127 173 121 S267 196 325 151 S389 81 451 108 S535 160 654 63"
            className="map-road"
          />
          <path
            d="M80 70 C154 114 198 36 267 78 S365 213 429 174 S500 89 630 192"
            className="map-road muted"
          />

          {/* Active Logistics Routes */}
          <path
            d="M126 175 C205 142 253 173 325 151 S477 109 560 92"
            className="map-route"
          />
          {/* Dynamic Reroute Arc */}
          <path
            d="M325 151 C390 111 430 115 515 177"
            className="map-route secondary"
            strokeDasharray="6 4"
          />
          <path
            d="M451 108 C504 83 567 83 642 63"
            className="map-route dotted"
          />

          {/* Nodes */}
          <circle cx="126" cy="175" r="9" className="map-node donor" />
          <circle cx="325" cy="151" r="9" className="map-node rider" />
          <circle cx="560" cy="92" r="11" className="map-node shelter" />
          <circle cx="515" cy="177" r="11" className="map-node shelter light" />
          <circle cx="642" cy="63" r="8" className="map-node rider small" />

          {/* Animated radar pulses */}
          <circle cx="126" cy="175" r="16" className="map-pulse" />
          <circle cx="560" cy="92" r="19" className="map-pulse orange-pulse" />
          <circle cx="325" cy="151" r="14" className="map-pulse" />
        </svg>

        <div className="map-label donor-label">
          <span />
          Donor Hub A (Banquet Hall)
        </div>
        <div className="map-label shelter-label">
          <span />
          Shelter B (Relief Camp)
        </div>
        <div className="map-label rider-label">
          <span />
          Rider #07 (In Transit)
        </div>
      </div>

      <div className="map-footer">
        <span>
          <span className="map-status-dot" />
          12 riders moving
        </span>
        <span>4 destination changes</span>
        <strong>+ 2.8m average buffer</strong>
      </div>
    </section>
  )
}
