import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useVigilo } from '../context/VigiloContext'
import { MobileTopBar } from './components/MobileTopBar'
import { MobileBottomNav, MobileTabId } from './components/MobileBottomNav'
import { MobileDispatchView } from './views/MobileDispatchView'
import { MobileActiveRunView } from './views/MobileActiveRunView'
import { MobileCustodyScanView } from './views/MobileCustodyScanView'
import { MobileSheltersDirectoryView } from './views/MobileSheltersDirectoryView'
import { MobileRiderProfileView } from './views/MobileRiderProfileView'
import { Batch, Shelter } from '../api/client'
import './mobileStyles.css'

interface MobileAppRootProps {
  onExitToWeb?: () => void
  isNativeApp?: boolean
}

export function MobileAppRoot({ onExitToWeb, isNativeApp = false }: MobileAppRootProps) {
  const {
    batches,
    shelters,
    triggerReroute,
    rerouteResolved,
  } = useVigilo()

  const [activeTab, setActiveTab] = useState<MobileTabId>('active')
  const [isOnline, setIsOnline] = useState<boolean>(true)
  const [deviceFrameMode, setDeviceFrameMode] = useState<boolean>(false)
  const [toastMessage, setToastMessage] = useState<string>('')

  const showMobileToast = (msg: string) => {
    setToastMessage(msg)
    window.setTimeout(() => setToastMessage(''), 3500)
  }

  const handleAcceptBatch = (batch: Batch) => {
    showMobileToast(`Accepted ${batch.item_type} (${batch.available_quantity} portions). Safe bio-window locked.`)
  }

  const handleHandoffComplete = () => {
    showMobileToast('✓ Handoff Cryptographically Verified! Zero Loss Invariant Passed.')
    setTimeout(() => {
      setActiveTab('profile')
    }, 1500)
  }

  const handleNavigateToShelter = (shelter: Shelter) => {
    showMobileToast(`Targeting ${shelter.name} on mobile turn-by-turn radar.`)
    setActiveTab('active')
  }

  // The actual mobile view content
  const mobileScreenContent = (
    <div className="mobile-app-viewport">
      {/* 1. Mobile Status & Navigation Top Bar */}
      <MobileTopBar
        isOnline={isOnline}
        isNativeApp={isNativeApp}
        onToggleOnline={() => {
          const next = !isOnline
          setIsOnline(next)
          showMobileToast(next ? 'Status: ONLINE (Mesh GPS active)' : 'Status: PAUSED')
        }}
        onExitMobile={isNativeApp ? undefined : onExitToWeb}
      />

      {/* 2. Toast Notification Bar */}
      <AnimatePresence>
        {toastMessage && (
          <motion.div
            className="mobile-toast-pill"
            initial={{ opacity: 0, y: -20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -20, scale: 0.95 }}
            transition={{ duration: 0.2 }}
          >
            <span>{toastMessage}</span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* 3. Main Operational View Area */}
      <main className="mobile-main-body">
        <AnimatePresence mode="wait">
          {activeTab === 'dispatch' && (
            <motion.div
              key="mobile-tab-dispatch"
              className="mobile-tab-wrapper"
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 10 }}
              transition={{ duration: 0.2 }}
            >
              <MobileDispatchView
                batches={batches}
                onAcceptBatch={handleAcceptBatch}
                onOpenActiveRun={() => setActiveTab('active')}
              />
            </motion.div>
          )}

          {activeTab === 'active' && (
            <motion.div
              key="mobile-tab-active"
              className="mobile-tab-wrapper"
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.98 }}
              transition={{ duration: 0.2 }}
            >
              <MobileActiveRunView
                onOpenScanHandoff={() => setActiveTab('scan')}
                onTriggerDivert={triggerReroute}
                isDiverted={rerouteResolved}
              />
            </motion.div>
          )}

          {activeTab === 'scan' && (
            <motion.div
              key="mobile-tab-scan"
              className="mobile-tab-wrapper"
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -15 }}
              transition={{ duration: 0.2 }}
            >
              <MobileCustodyScanView onHandoffComplete={handleHandoffComplete} />
            </motion.div>
          )}

          {activeTab === 'shelters' && (
            <motion.div
              key="mobile-tab-shelters"
              className="mobile-tab-wrapper"
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -10 }}
              transition={{ duration: 0.2 }}
            >
              <MobileSheltersDirectoryView
                shelters={shelters}
                onNavigateToShelter={handleNavigateToShelter}
              />
            </motion.div>
          )}

          {activeTab === 'profile' && (
            <motion.div
              key="mobile-tab-profile"
              className="mobile-tab-wrapper"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
            >
              <MobileRiderProfileView
                onReportHazard={(h) => showMobileToast(`Alerted dispatcher: ${h}`)}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* 4. Bottom Thumb Navigation */}
      <MobileBottomNav
        activeTab={activeTab}
        onTabChange={(tab) => setActiveTab(tab)}
        hasActiveTrip={true}
        availableCount={batches.filter((b) => b.available_quantity > 0).length}
      />
    </div>
  )

  // If running natively inside Android APK, render cleanly without desktop test frames
  if (isNativeApp) {
    return (
      <div className="mobile-app-wrapper-container is-native-android in-full-viewport">
        <div className="mobile-app-standalone-container">
          {mobileScreenContent}
        </div>
      </div>
    )
  }

  // Outer Wrapper: Allows switching between Full Native viewport and Desktop Device Mockup Frame
  return (
    <div className={`mobile-app-wrapper-container ${deviceFrameMode ? 'in-device-frame' : 'in-full-viewport'}`}>
      {/* Floating Mode Switcher for Desktop Testers */}
      <div className="mobile-frame-controls-bar">
        <button
          className="mode-toggle-chip"
          onClick={() => setDeviceFrameMode(!deviceFrameMode)}
          title="Toggle between phone device frame and full viewport"
        >
          <span>{deviceFrameMode ? '📱 iPhone Mockup' : '🖥️ Responsive Full Screen'}</span>
        </button>

        {onExitToWeb && (
          <button
            className="exit-mobile-chip"
            onClick={onExitToWeb}
            title="Return to Desktop Mission Control"
          >
            <span>Exit to Web Command ↗</span>
          </button>
        )}
      </div>

      {deviceFrameMode ? (
        <div className="iphone-device-chassis">
          <div className="iphone-notch">
            <span className="camera-dot" />
            <span className="speaker-slit" />
          </div>
          {mobileScreenContent}
          <div className="iphone-home-indicator" />
        </div>
      ) : (
        <div className="mobile-app-standalone-container">
          {mobileScreenContent}
        </div>
      )}
    </div>
  )
}
