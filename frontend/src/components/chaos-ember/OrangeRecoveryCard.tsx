import { motion } from 'framer-motion'
import { Icon } from '../Icon'

interface OrangeRecoveryCardProps {
  onInject: () => void
}

export function OrangeRecoveryCard({ onInject }: OrangeRecoveryCardProps) {
  return (
    <motion.section
      className="orange-recovery-card"
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4 }}
    >
      <div className="orange-card-top">
        <span className="orange-kicker">
          <Icon name="spark" size={14} />
          SELF-HEALING ENGINE
        </span>
        <button className="orange-action" onClick={onInject}>
          <Icon name="zap" size={14} />
          Inject live failure
        </button>
      </div>

      <div className="orange-card-copy">
        <h2>
          When plans
          <br />
          break, aid moves.
        </h2>
        <p>
          Test a disruption and watch the network protect safety, custody, and bio-expiry windows.
        </p>
      </div>

      <div className="orange-card-footer">
        <div>
          <strong>125</strong>
          <span>automated recoveries today</span>
        </div>
        <div className="mini-orbit" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
      </div>
    </motion.section>
  )
}
