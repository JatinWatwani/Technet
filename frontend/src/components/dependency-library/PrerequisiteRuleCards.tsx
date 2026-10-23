import { motion } from 'framer-motion'
import { Icon } from '../Icon'
import { SectionHeading } from '../common/SectionHeading'
import type { IconName } from '../../types'

interface RuleItem {
  tone: string
  icon: IconName
  title: string
  rule: string
  state: string
  detail: string
}

const RULES: RuleItem[] = [
  {
    tone: 'lavender',
    icon: 'layers',
    title: 'Raw rations',
    rule: 'Clean water + cooking fuel',
    state: 'Verified',
    detail: 'Blocks matching if receiver lacks active boiling fuel or potable water source.',
  },
  {
    tone: 'blue',
    icon: 'shield',
    title: 'Infant formula',
    rule: 'Sterile water required',
    state: 'Verified',
    detail: 'Mandates medical-grade sterile water and cold-pack custody chain.',
  },
  {
    tone: 'mint',
    icon: 'clock',
    title: 'Cooked meals',
    rule: '75m bio-expiry window',
    state: 'Monitored',
    detail: 'Continuous deadline clock tracking ambient temperature exposure.',
  },
]

export function PrerequisiteRuleCards() {
  return (
    <section className="panel dependency-panel">
      <SectionHeading
        icon="book"
        eyebrow="DEPENDENCY LIBRARY"
        title="Rules that keep aid usable"
        action={
          <button className="text-button">
            View library <Icon name="chevron" size={14} />
          </button>
        }
      />

      <div className="rule-row">
        {RULES.map((item, index) => (
          <motion.article
            key={item.title}
            className={`rule-card ${item.tone}`}
            initial={{ opacity: 0, filter: 'blur(6px)', scale: 0.96 }}
            animate={{ opacity: 1, filter: 'blur(0px)', scale: 1 }}
            transition={{ duration: 0.4, delay: index * 0.08, ease: [0.22, 1, 0.36, 1] }}
            whileHover={{ y: -3, transition: { duration: 0.2 } }}
          >
            <div className="rule-icon">
              <Icon name={item.icon} size={17} />
            </div>
            <div>
              <strong>{item.title}</strong>
              <span>{item.rule}</span>
            </div>
            <span className="rule-state">
              <Icon name="check" size={12} />
              {item.state}
            </span>
          </motion.article>
        ))}
      </div>
    </section>
  )
}
