import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Icon } from '../../components/Icon'
import { SwipeToConfirm } from '../components/SwipeToConfirm'
import { Batch } from '../../api/client'

interface MobileDispatchViewProps {
  batches: Batch[]
  onAcceptBatch: (batch: Batch) => void
  onOpenActiveRun: () => void
}

export function MobileDispatchView({
  batches,
  onAcceptBatch,
  onOpenActiveRun,
}: MobileDispatchViewProps) {
  const [selectedBatch, setSelectedBatch] = useState<Batch | null>(null)
  const [acceptedBatchId, setAcceptedBatchId] = useState<string | null>(null)

  // Filter available batches
  const availableBatches = batches.filter((b) => b.available_quantity > 0)

  const handleConfirmAccept = (batch: Batch) => {
    setAcceptedBatchId(batch.id)
    onAcceptBatch(batch)
    setTimeout(() => {
      onOpenActiveRun()
    }, 1200)
  }

  return (
    <div className="mobile-view-content mobile-dispatch-view">
      {/* 1. Header Banner */}
      <div className="mobile-section-header">
        <div>
          <span className="mobile-eyebrow">RELIEF DISPATCH QUEUE</span>
          <h2 className="mobile-title">Nearby Rations Available</h2>
        </div>
        <span className="mobile-count-pill">{availableBatches.length} READY</span>
      </div>

      {/* 2. Urgent Live Announcement Card */}
      <div className="mobile-alert-banner">
        <span className="alert-pulse-dot" />
        <div className="alert-banner-text">
          <strong>Flash Flood Hazard: Sector 4 North Corridor</strong>
          <small>Automated resilience routing active. Overcapacity shelters auto-bypassed.</small>
        </div>
      </div>

      {/* 3. Available Batch Offers List */}
      <div className="mobile-offers-stack">
        {availableBatches.map((batch) => {
          const isSelected = selectedBatch?.id === batch.id
          const isAccepted = acceptedBatchId === batch.id
          const isColdChain = batch.item_rules?.storage_requirement === 'COLD_CHAIN'
          const safeWindowMins = batch.item_rules?.safe_handling_minutes || 48

          return (
            <motion.div
              key={batch.id}
              className={`mobile-offer-card ${isSelected ? 'is-selected' : ''} ${isAccepted ? 'is-accepted' : ''}`}
              whileTap={{ scale: 0.98 }}
              onClick={() => setSelectedBatch(batch)}
            >
              <div className="offer-card-top">
                <div className="offer-badge-row">
                  <span className={`offer-type-tag ${isColdChain ? 'tag-cold' : 'tag-meal'}`}>
                    {isColdChain ? '❄️ Cold-Chain' : '🍲 Hot Meals'}
                  </span>
                  <span className="offer-bio-timer">
                    <Icon name="clock" size={12} />
                    <span>{safeWindowMins}m safe window</span>
                  </span>
                </div>
                <div className="offer-qty-pill">
                  {batch.available_quantity} portions
                </div>
              </div>

              <div className="offer-card-body">
                <h3 className="offer-item-name">{batch.item_type}</h3>
                <div className="offer-route-step">
                  <span className="route-node-icon origin">●</span>
                  <span className="route-node-text">
                    <strong>Pickup:</strong> {batch.donor_id.replace('donor_', '').replace(/_/g, ' ').toUpperCase()} (0.8 km)
                  </span>
                </div>
                <div className="offer-route-step">
                  <span className="route-node-icon destination">▼</span>
                  <span className="route-node-text">
                    <strong>Destination:</strong> Relief Camp B (+138 Capacity Ready)
                  </span>
                </div>
              </div>

              {/* Swipe to Accept or Expanded Drawer */}
              <div className="offer-card-footer" onClick={(e) => e.stopPropagation()}>
                {isAccepted ? (
                  <div className="offer-accepted-banner">
                    <span className="check-icon">✓</span>
                    <span>Consignment Locked! Launching Turn-by-Turn GPS...</span>
                  </div>
                ) : (
                  <SwipeToConfirm
                    label="Slide to Accept Mission"
                    confirmedLabel="Accepted! Loading GPS..."
                    onConfirm={() => handleConfirmAccept(batch)}
                  />
                )}
              </div>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}
