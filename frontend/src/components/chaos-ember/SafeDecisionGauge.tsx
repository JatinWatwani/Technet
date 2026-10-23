import { Icon } from '../Icon'
import { SectionHeading } from '../common/SectionHeading'

interface SafeDecisionGaugeProps {
  onInject: (type?: string) => void
}

export function SafeDecisionGauge({ onInject }: SafeDecisionGaugeProps) {
  return (
    <section className="panel gauge-panel">
      <SectionHeading
        icon="clock"
        eyebrow="FLEET HEALTH"
        title="Last-safe-decision"
        action={
          <span className="live-tag">
            <span className="live-pulse" />
            Live
          </span>
        }
      />

      <div className="gauge-wrap">
        <svg
          className="gauge-svg"
          viewBox="0 0 260 150"
          role="img"
          aria-label="236 second safe recovery buffer"
        >
          <defs>
            <linearGradient id="gauge-gradient" x1="0" x2="1">
              <stop offset="0" stopColor="#ffb26d" />
              <stop offset=".65" stopColor="#ff713d" />
              <stop offset="1" stopColor="#e64a20" />
            </linearGradient>
          </defs>
          <path d="M32 128a98 98 0 0 1 196 0" className="gauge-track" />
          <path d="M32 128a98 98 0 0 1 196 0" className="gauge-value" />
          <path d="M32 128a98 98 0 0 1 196 0" className="gauge-ticks" />
          <circle cx="130" cy="30" r="4" className="gauge-knob" />
        </svg>

        <div className="gauge-center">
          <strong>236</strong>
          <span>seconds buffer</span>
          <em>
            <Icon name="check" size={12} /> Safe to recover
          </em>
        </div>
      </div>

      <div className="inject-row">
        <span>Failure injectors</span>
        <button onClick={() => onInject('freeze')} title="Simulate Volunteer Stall">
          <Icon name="pause" size={13} />
          Freeze rider
        </button>
        <button onClick={() => onInject('close')} title="Simulate Shelter Overflow">
          <Icon name="home" size={13} />
          Close shelter
        </button>
        <button onClick={() => onInject('clock')} title="Fast-Forward 15 minutes">
          <Icon name="clock" size={13} />
          +15m
        </button>
      </div>
    </section>
  )
}
