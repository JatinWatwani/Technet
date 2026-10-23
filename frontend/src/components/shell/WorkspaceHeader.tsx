import { motion, AnimatePresence } from 'framer-motion'
import { Icon } from '../Icon'
import type { Mode } from '../../types'

interface WorkspaceHeaderProps {
  mode: Mode
  title: string
  currentTime: string
  onModeSwitch: () => void
  onReplayColdStart?: () => void
}

export function WorkspaceHeader({
  mode,
  title,
  currentTime,
  onModeSwitch,
  onReplayColdStart,
}: WorkspaceHeaderProps) {
  const words = title.split(' ')

  return (
    <div className="workspace-header">
      <div className="title-block">
        <div className="eyebrow">
          <span className="eyebrow-dot" />
          {mode === 'live' ? 'MONDAY, OCT 23 · LIVE NETWORK' : 'SIMULATION RUN 04 · FAILURE RECOVERY'}
        </div>
        <AnimatePresence mode="wait">
          <motion.h1
            key={title + mode}
            style={{ display: 'inline-flex', flexWrap: 'wrap', gap: '0.28em' }}
          >
            {words.map((word, index) => (
              <motion.span
                key={`${word}-${index}`}
                initial={{ opacity: 0, filter: 'blur(14px)', y: 10 }}
                animate={{ opacity: 1, filter: 'blur(0px)', y: 0 }}
                exit={{ opacity: 0, filter: 'blur(8px)', y: -8 }}
                transition={{
                  duration: 0.42,
                  delay: index * 0.09,
                  ease: [0.22, 1, 0.36, 1],
                }}
              >
                {word}
              </motion.span>
            ))}
            <motion.span
              className="title-period"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: words.length * 0.09 + 0.1 }}
            >
              .
            </motion.span>
          </motion.h1>
        </AnimatePresence>
        <p>
          {mode === 'live'
            ? 'Make the next safe decision before the clock makes it for you.'
            : 'Stress-test the network, preserve physical custody, and watch self-healing recovery happen.'}
        </p>
      </div>

      <div className="header-controls">
        {onReplayColdStart && (
          <button
            className="outline-button"
            onClick={onReplayColdStart}
            title="Replay Frame 1-3 Cold Start Animation"
            style={{ padding: '7px 11px', fontSize: '10px' }}
          >
            <Icon name="refresh" size={13} />
            Replay Boot Sequence
          </button>
        )}
        <div className="clock-card">
          <span>Last-safe-decision clock</span>
          <strong>{currentTime}</strong>
          <em>healthy buffer</em>
        </div>
        <button
          className={`mode-mini ${mode === 'chaos' ? 'chaos' : ''}`}
          onClick={onModeSwitch}
        >
          <span className="mode-mini-icon">
            <Icon name={mode === 'live' ? 'activity' : 'flame'} size={15} />
          </span>
          <span>{mode === 'live' ? 'Live network' : 'Chaos studio'}</span>
          <Icon name="chevron" size={14} />
        </button>
      </div>
    </div>
  )
}
