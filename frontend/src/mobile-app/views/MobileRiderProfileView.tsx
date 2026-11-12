import React, { useState } from 'react'
import { Icon } from '../../components/Icon'

interface MobileRiderProfileViewProps {
  onReportHazard?: (hazard: string) => void
}

export function MobileRiderProfileView({ onReportHazard }: MobileRiderProfileViewProps) {
  const [offlineCacheEnabled, setOfflineCacheEnabled] = useState(true)
  const [reportedMsg, setReportedMsg] = useState('')

  const handleReport = (hazard: string) => {
    setReportedMsg(`Reported: ${hazard}. Mesh nodes notified.`)
    onReportHazard?.(hazard)
    setTimeout(() => setReportedMsg(''), 4000)
  }

  return (
    <div className="mobile-view-content mobile-profile-view">
      {/* 1. Courier Identity Card */}
      <div className="mobile-courier-hero-card">
        <div className="courier-badge-large">
          <Icon name="bike" size={32} />
          <span className="badge-ring-pulse" />
        </div>
        <h2 className="courier-big-name">Vikram Sharma</h2>
        <span className="courier-role-title">Rapid Relief Lead · Volunteer Mesh Partner</span>
        <div className="courier-vehicle-pill">
          <span>🛵 Bajaj Pulsar 150 · Capacity: 40 units</span>
        </div>
      </div>

      {/* 2. Impact & Verified Ledger Stats */}
      <div className="mobile-stats-grid">
        <div className="mobile-stat-box">
          <span className="stat-big-num text-emerald">1,420</span>
          <small>MEALS DELIVERED</small>
        </div>
        <div className="mobile-stat-box">
          <span className="stat-big-num text-emerald">100%</span>
          <small>SAFE HANDOFFS</small>
        </div>
        <div className="mobile-stat-box">
          <span className="stat-big-num text-emerald">0 Loss</span>
          <small>MASS CONSERVATION</small>
        </div>
        <div className="mobile-stat-box">
          <span className="stat-big-num">14.8 km</span>
          <small>CORRIDOR TRANSIT</small>
        </div>
      </div>

      {/* 3. Operational Preferences & Offline Cache */}
      <div className="mobile-card-section">
        <h3 className="section-title">Field Offline Resilience</h3>
        <div className="toggle-row">
          <div>
            <strong>Offline GPS Map Cache</strong>
            <small>Pre-downloaded disaster tiles for Sector 4 & 9</small>
          </div>
          <button
            className={`mobile-switch-btn ${offlineCacheEnabled ? 'is-active' : ''}`}
            onClick={() => setOfflineCacheEnabled(!offlineCacheEnabled)}
          >
            <span className="switch-knob" />
          </button>
        </div>
      </div>

      {/* 4. One-Tap Quick Hazard Reporting */}
      <div className="mobile-card-section">
        <h3 className="section-title">Quick Road Hazard Broadcast</h3>
        {reportedMsg && <div className="hazard-toast">{reportedMsg}</div>}
        <div className="hazard-buttons-grid">
          <button
            className="hazard-btn"
            onClick={() => handleReport('Flash flood road blockage near Sector 4')}
          >
            🌊 Flash Flood Water
          </button>
          <button
            className="hazard-btn"
            onClick={() => handleReport('Bridge crossing closed - debris obstruction')}
          >
            🚧 Bridge Blocked
          </button>
          <button
            className="hazard-btn"
            onClick={() => handleReport('Shelter A intake gate jammed')}
          >
            ⛔ Gate Overflow
          </button>
        </div>
      </div>

      {/* 5. Cryptographic Device Hash */}
      <div className="mobile-crypto-footer">
        <span>Vigilio Field Mesh Node: <code>0x4b9a...712c</code></span>
        <span>Peer-to-Peer Offline Verification Active</span>
      </div>
    </div>
  )
}
