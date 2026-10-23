import { motion } from 'framer-motion'
import { Icon } from '../Icon'
import type { IconName } from '../../types'

interface ProtocolCard {
  id: string
  title: string
  phonetic: string
  tag: string
  rule: string
  state: 'Verified' | 'Monitored' | 'Pending'
  tone: 'lavender' | 'blue' | 'mint'
  icon: IconName
  specs: string[]
}

const PROTOCOLS: ProtocolCard[] = [
  {
    id: 'resilient',
    title: 'Resilient Custody',
    phonetic: '/rɪˈzɪl.jənt ˈkʌs.tə.di/',
    tag: 'protocol · bio-expiry',
    rule: 'Cooked meals require strict 75m thermal window. Any stalled volunteer triggers automatic sub-ticket split.',
    state: 'Verified',
    tone: 'lavender',
    icon: 'clock',
    specs: ['75m bio-safe threshold', '180 meal batch max', 'Split across 5 riders'],
  },
  {
    id: 'meticulous',
    title: 'Meticulous Cold-Chain',
    phonetic: '/məˈtɪk.jə.ləs koʊld-tʃeɪn/',
    tag: 'protocol · medical aid',
    rule: 'Insulin and infant therapeutics mandate verified cold-pack telemetry and dual-rider escort custody.',
    state: 'Verified',
    tone: 'blue',
    icon: 'shield',
    specs: ['2°C to 8°C continuous sensor', 'Dual-rider handover proof', 'Zero silent release'],
  },
  {
    id: 'prerequisite',
    title: 'Prerequisite Coupling',
    phonetic: '/prɪˈrek.wə.zɪt ˈkʌp.lɪŋ/',
    tag: 'protocol · dependency',
    rule: 'Raw ration kits and powdered nutrition cannot be matched to shelters lacking potable water and boiling fuel.',
    state: 'Monitored',
    tone: 'mint',
    icon: 'layers',
    specs: ['Potable water check', 'Cooking fuel verified', 'Auto-reroute if water cut'],
  },
]

export function DedicatedLibraryView() {
  return (
    <div className="dedicated-library-view">
      <div className="library-subhead">
        <p>
          Formal verification invariants governing perishables, custody handovers, and supply safety prerequisites.
        </p>
        <span className="library-counter">3 active protocols</span>
      </div>

      <div className="word-library-grid">
        {PROTOCOLS.map((protocol, index) => (
          <motion.article
            key={protocol.id}
            className={`word-card ${protocol.tone}`}
            initial={{
              opacity: 0,
              filter: 'blur(8px)',
              scale: 0.95,
              x: -16,
            }}
            animate={{
              opacity: 1,
              filter: 'blur(0px)',
              scale: 1,
              x: 0,
            }}
            transition={{
              duration: 0.5,
              delay: index * 0.12,
              ease: [0.22, 1, 0.36, 1],
            }}
            whileHover={{ y: -4, transition: { duration: 0.2 } }}
          >
            <div className="word-card-top">
              <span className="word-tag">{protocol.tag}</span>
              <span className="word-state">
                <Icon name="check" size={13} />
                {protocol.state}
              </span>
            </div>

            <div className="word-card-body">
              <div className="word-title-row">
                <h2>{protocol.title}</h2>
                <button
                  className="audio-button"
                  aria-label={`Listen to ${protocol.title}`}
                  title="Audio Telemetry Briefing"
                >
                  <Icon name="activity" size={15} />
                </button>
              </div>
              <span className="word-phonetic">{protocol.phonetic}</span>
              <p className="word-rule">{protocol.rule}</p>
            </div>

            <div className="word-card-footer">
              {protocol.specs.map((spec, i) => (
                <span key={i} className="spec-chip">
                  {spec}
                </span>
              ))}
            </div>
          </motion.article>
        ))}
      </div>
    </div>
  )
}
