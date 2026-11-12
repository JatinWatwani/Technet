import React, { useState, useEffect } from 'react'
import { Icon } from '../../components/Icon'

interface MobileTopBarProps {
  isOnline: boolean
  onToggleOnline: () => void
  onExitMobile?: () => void
  isNativeApp?: boolean
}

export function MobileTopBar({ isOnline, onToggleOnline, onExitMobile, isNativeApp = false }: MobileTopBarProps) {
  const [timeStr, setTimeStr] = useState<string>('09:41')

  useEffect(() => {
    const updateTime = () => {
      const now = new Date()
      setTimeStr(now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false }))
    }
    updateTime()
    const interval = setInterval(updateTime, 10000)
    return () => clearInterval(interval)
  }, [])

  return (
    <header className="mobile-native-topbar">
      {/* 1. Mobile Status Bar (Time, Signals, Battery) - only shown when previewing inside desktop web */}
      {!isNativeApp && (
        <div className="mobile-system-status-row">
        <span className="mobile-system-time">{timeStr}</span>
        <div className="mobile-system-icons">
          <span className="system-pill-chip">5G</span>
          <svg width="15" height="11" viewBox="0 0 15 11" fill="none">
            <rect x="0.5" y="8" width="2" height="3" rx="0.5" fill="currentColor"/>
            <rect x="4" y="5.5" width="2" height="5.5" rx="0.5" fill="currentColor"/>
            <rect x="7.5" y="3" width="2" height="8" rx="0.5" fill="currentColor"/>
            <rect x="11" y="0.5" width="2" height="10.5" rx="0.5" fill="currentColor"/>
          </svg>
          <div className="mobile-battery-pill">
            <div className="battery-level-fill" style={{ width: '88%' }}></div>
          </div>
        </div>
      </div>
    )}

      {/* 2. Courier App Navigation Header */}
      <div className="mobile-partner-nav-row">
        <div className="mobile-courier-profile">
          <div className="courier-mobile-avatar">
            <Icon name="bike" size={18} />
            <span className="courier-live-dot" />
          </div>
          <div className="courier-title-col">
            <div className="courier-id-tag">COURIER #07</div>
            <strong className="courier-name-text">Vikram Sharma</strong>
          </div>
        </div>

        <div className="mobile-nav-actions">
          {/* Online / Offline Duty Switch */}
          <button
            className={`mobile-duty-pill ${isOnline ? 'is-online' : 'is-offline'}`}
            onClick={onToggleOnline}
            title={isOnline ? 'Active on courier mesh' : 'Paused duty'}
          >
            <span className="duty-dot" />
            <span>{isOnline ? 'ONLINE' : 'PAUSED'}</span>
          </button>

          {/* Exit / Switch to Web Command Center */}
          {onExitMobile && (
            <button
              className="mobile-exit-btn"
              onClick={onExitMobile}
              title="Return to Desktop Mission Control"
            >
              <Icon name="command" size={14} />
            </button>
          )}
        </div>
      </div>
    </header>
  )
}
