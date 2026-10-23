import { motion } from 'framer-motion'
import { Icon } from '../Icon'
import type { IconName } from '../../types'

interface MetricProps {
  label: string
  value: string
  suffix?: string
  delta: string
  detail: string
  tone: 'mint' | 'purple' | 'orange'
  icon: IconName
  delay: number
}

function ChaosMetric({
  label,
  value,
  suffix,
  delta,
  detail,
  tone,
  icon,
  delay,
}: MetricProps) {
  const isPositive = delta.startsWith('+')
  return (
    <motion.article
      className={`chaos-metric ${tone}`}
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay }}
      whileHover={{ y: -2 }}
    >
      <div className="metric-icon">
        <Icon name={icon} size={17} />
      </div>
      <span className="metric-label">{label}</span>
      <div className="chaos-value">
        {value}
        {suffix && <small>{suffix}</small>}
      </div>
      <div className="metric-bottom">
        <span className="delta">
          <Icon name={isPositive ? 'arrowUp' : 'arrowDown'} size={12} />
          {delta}
        </span>
        <span>{detail}</span>
      </div>
    </motion.article>
  )
}

export function HeroKpiRow() {
  return (
    <div className="chaos-kpi-row">
      <ChaosMetric
        label="Meals saved"
        value="1,349"
        delta="+18%"
        detail="vs. nearest-feasible baseline"
        tone="mint"
        icon="box"
        delay={0.05}
      />
      <ChaosMetric
        label="Active reroutes"
        value="574"
        delta="−5%"
        detail="spoilage exposure"
        tone="purple"
        icon="route"
        delay={0.12}
      />
      <ChaosMetric
        label="Recovery speed"
        value="899"
        suffix="ms"
        delta="+12%"
        detail="median decision latency"
        tone="orange"
        icon="zap"
        delay={0.19}
      />
    </div>
  )
}
