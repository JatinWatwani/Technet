import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { Icon } from '../../components/Icon'
import { SwipeToConfirm } from '../components/SwipeToConfirm'

interface MobileCustodyScanViewProps {
  onHandoffComplete: () => void
}

export function MobileCustodyScanView({ onHandoffComplete }: MobileCustodyScanViewProps) {
  const [isScanning, setIsScanning] = useState(true)
  const [isVerified, setIsVerified] = useState(false)

  const handleSimulateScan = () => {
    setIsScanning(false)
    setIsVerified(true)
    if (typeof navigator !== 'undefined' && navigator.vibrate) {
      navigator.vibrate([80, 50, 80])
    }
  }

  const handleFinalSign = () => {
    onHandoffComplete()
  }

  return (
    <div className="mobile-view-content mobile-scan-view">
      {/* 1. Header */}
      <div className="mobile-section-header">
        <div>
          <span className="mobile-eyebrow">CHAIN OF CUSTODY VERIFICATION</span>
          <h2 className="mobile-title">Cryptographic Handoff</h2>
        </div>
        <span className="mobile-verified-badge">TLS 1.3 SECURE</span>
      </div>

      {/* 2. QR / Viewfinder Scanner */}
      <div className="scanner-viewfinder-card">
        <div className="viewfinder-frame">
          {/* Animated Scanner Laser */}
          {isScanning && (
            <motion.div
              className="scanner-laser"
              animate={{ y: [0, 180, 0] }}
              transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
            />
          )}

          <div className="viewfinder-corners">
            <span className="corner top-left" />
            <span className="corner top-right" />
            <span className="corner bottom-left" />
            <span className="corner bottom-right" />
          </div>

          <div className="viewfinder-center-qr">
            <svg width="90" height="90" viewBox="0 0 24 24" fill="none">
              <path d="M3 3h6v6H3V3zm12 0h6v6h-6V3zm0 12h6v6h-6v-6zm-12 0h6v6H3v-6zm3-10v2h2V5H6zm12 0v2h2V5h-2zm0 12v2h2v-2h-2zm-12 0v2h2v-2H6z" fill="#10B981" />
            </svg>
            <span className="qr-hash-label">CAMP-B::RECEIVE-GATE-09</span>
          </div>
        </div>

        <div className="scanner-instruction-strip">
          <Icon name="shield" size={16} />
          <span>Align shelter manager QR token inside viewfinder</span>
        </div>

        {isScanning && (
          <button className="simulate-scan-tap-btn" onClick={handleSimulateScan}>
            <span>Tap to Scan QR Code</span>
          </button>
        )}
      </div>

      {/* 3. Verified Custody Certificate */}
      {isVerified && (
        <motion.div
          className="custody-proof-card"
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          <div className="proof-header">
            <div className="proof-check-circle">✓</div>
            <div>
              <strong>Cryptographic Custody Match</strong>
              <small>Hash: 0x8f2d...4a9e · Zero Loss Invariant Verified</small>
            </div>
          </div>

          <div className="proof-specs-grid">
            <div className="proof-spec-item">
              <small>CARGO</small>
              <strong>40 Fresh Meals</strong>
            </div>
            <div className="proof-spec-item">
              <small>DESTINATION</small>
              <strong>Relief Camp B</strong>
            </div>
            <div className="proof-spec-item">
              <small>SAFE WINDOW</small>
              <strong className="text-emerald">+18m Remaining</strong>
            </div>
            <div className="proof-spec-item">
              <small>SPOILAGE LOSS</small>
              <strong className="text-emerald">0.00% (Zero)</strong>
            </div>
          </div>

          <div className="proof-action-row">
            <SwipeToConfirm
              label="Slide to Complete Handoff"
              confirmedLabel="Delivery Logged! +40 Meals Received"
              onConfirm={handleFinalSign}
            />
          </div>
        </motion.div>
      )}
    </div>
  )
}
