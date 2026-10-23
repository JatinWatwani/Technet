import { Icon } from '../Icon'
import type { Mode } from '../../types'

interface BottomModeSwitcherProps {
  mode: Mode
  onSwitch: () => void
  chaosBadgeCount?: number
}

export function BottomModeSwitcher({
  mode,
  onSwitch,
  chaosBadgeCount = 4,
}: BottomModeSwitcherProps) {
  return (
    <div className="bottom-switcher">
      <button
        className={mode === 'live' ? 'is-active' : ''}
        onClick={mode === 'live' ? undefined : onSwitch}
      >
        <Icon name="activity" size={15} />
        Live network
      </button>
      <button
        className={mode === 'chaos' ? 'is-active chaos-active' : ''}
        onClick={mode === 'chaos' ? undefined : onSwitch}
      >
        <Icon name="flame" size={15} />
        Chaos studio
        <span className="switcher-alert">{chaosBadgeCount}</span>
      </button>
      <div className="switcher-thumb">
        <span />
      </div>
    </div>
  )
}
