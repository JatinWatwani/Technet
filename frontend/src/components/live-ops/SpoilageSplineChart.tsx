import { Icon } from '../Icon'
import { SectionHeading } from '../common/SectionHeading'

export function SpoilageSplineChart() {
  return (
    <section className="panel chart-panel">
      <SectionHeading
        icon="activity"
        eyebrow="DECISION SUPPORT"
        title="Spoilage risk & safe delivery"
        action={
          <button className="icon-button quiet" aria-label="Chart settings">
            <Icon name="more" size={18} />
          </button>
        }
      />

      <div className="chart-meta">
        <div>
          <span className="big-number">
            86<span className="number-unit">%</span>
          </span>
          <span className="metric-caption">safe delivery confidence</span>
        </div>
        <div className="chart-legend">
          <span>
            <i className="legend-dot purple" />
            Delivered volume
          </span>
          <span>
            <i className="legend-dot blue" />
            In transit
          </span>
          <span>
            <i className="legend-dot coral" />
            Spoilage threshold
          </span>
        </div>
      </div>

      <div className="risk-chart">
        <div className="chart-y-labels">
          <span>100</span>
          <span>75</span>
          <span>50</span>
          <span>25</span>
          <span>0</span>
        </div>
        <svg
          viewBox="0 0 760 238"
          role="img"
          aria-label="Three-line spline chart for delivered volume, in transit load, and spoilage risk threshold"
        >
          <defs>
            <linearGradient id="purple-fill" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0" stopColor="#8f7bff" stopOpacity=".28" />
              <stop offset="1" stopColor="#8f7bff" stopOpacity="0" />
            </linearGradient>
            <linearGradient id="blue-fill" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0" stopColor="#5bc9ef" stopOpacity=".24" />
              <stop offset="1" stopColor="#5bc9ef" stopOpacity="0" />
            </linearGradient>
          </defs>

          {[26, 72, 118, 164, 210].map((y) => (
            <line key={y} x1="0" x2="760" y1={y} y2={y} className="chart-gridline" />
          ))}

          {/* Area under purple curve */}
          <path
            d="M0 184 C55 177 77 153 125 162 S195 168 230 125 S306 90 345 116 S417 168 464 119 S530 77 574 103 S640 122 678 63 S728 53 760 30 L760 210 L0 210Z"
            fill="url(#purple-fill)"
          />
          {/* Purple spline line */}
          <path
            d="M0 184 C55 177 77 153 125 162 S195 168 230 125 S306 90 345 116 S417 168 464 119 S530 77 574 103 S640 122 678 63 S728 53 760 30"
            className="chart-line purple-line"
          />

          {/* Area under blue curve */}
          <path
            d="M0 144 C50 139 89 165 125 135 S194 111 231 140 S306 150 347 96 S419 111 464 86 S538 121 578 73 S646 94 687 75 S736 79 760 57 L760 210 L0 210Z"
            fill="url(#blue-fill)"
          />
          {/* Blue spline line */}
          <path
            d="M0 144 C50 139 89 165 125 135 S194 111 231 140 S306 150 347 96 S419 111 464 86 S538 121 578 73 S646 94 687 75 S736 79 760 57"
            className="chart-line blue-line"
          />

          {/* Coral dashed threshold */}
          <path
            d="M0 201 C78 196 103 198 156 189 S255 190 300 182 S393 189 434 177 S517 180 564 165 S657 169 700 139 S740 117 760 104"
            className="chart-line coral-line"
            strokeDasharray="5 7"
          />

          {/* Key data markers */}
          <circle cx="678" cy="63" r="5" className="chart-point purple-point" />
          <circle cx="687" cy="75" r="5" className="chart-point blue-point" />
          <circle cx="700" cy="139" r="5" className="chart-point coral-point" />
        </svg>

        <div className="chart-x-labels">
          <span>09:00</span>
          <span>11:00</span>
          <span>13:00</span>
          <span>15:00</span>
          <span>17:00</span>
          <span>19:00</span>
        </div>
      </div>

      <div className="chart-footer">
        <span>
          <Icon name="clock" size={14} /> Decision window closes in <strong>08:42</strong>
        </span>
        <span className="positive-label">
          <Icon name="arrowUp" size={13} /> 12.4% safer than baseline
        </span>
      </div>
    </section>
  )
}
