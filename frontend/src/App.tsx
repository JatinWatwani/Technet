import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { CyberTopNav } from './components/cyber-vigilio/CyberTopNav'
import { DarkHeroStage } from './components/cyber-vigilio/DarkHeroStage'
import { SourcesBentoCard } from './components/cyber-vigilio/SourcesBentoCard'
import { AlertsBentoCard } from './components/cyber-vigilio/AlertsBentoCard'
import { AutomationBentoCard } from './components/cyber-vigilio/AutomationBentoCard'
import { AssetsBentoCard } from './components/cyber-vigilio/AssetsBentoCard'
import { BottomTimelineBar } from './components/cyber-vigilio/BottomTimelineBar'
import { AlertsTableModal } from './components/cyber-vigilio/AlertsTableModal'
import { FullTimelineDrawer } from './components/cyber-vigilio/FullTimelineDrawer'
import { QuickCreateModal } from './components/cyber-vigilio/QuickCreateModal'
import { TelemetryFilterDrawer } from './components/cyber-vigilio/TelemetryFilterDrawer'
import { SystemSettingsModal } from './components/cyber-vigilio/SystemSettingsModal'
import { KeyAlertsView } from './components/cyber-vigilio/KeyAlertsView'
import { InsightsView } from './components/cyber-vigilio/InsightsView'
import { ExecutionsView } from './components/cyber-vigilio/ExecutionsView'
import { OperationsMatrixView } from './components/cyber-vigilio/OperationsMatrixView'
import { LiveFleetMapView } from './components/cyber-vigilio/LiveFleetMapView'
import { VigilioLandingPage } from './components/landing/VigilioLandingPage'

export function App() {
  const [activeTab, setActiveTab] = useState('overview')
  const [theme, setTheme] = useState<'light' | 'dark'>('light')
  const [isAlertsTableOpen, setIsAlertsTableOpen] = useState(false)
  const [isTimelineDrawerOpen, setIsTimelineDrawerOpen] = useState(false)
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [isFilterDrawerOpen, setIsFilterDrawerOpen] = useState(false)
  const [isSettingsModalOpen, setIsSettingsModalOpen] = useState(false)
  const [isMatrixActive, setIsMatrixActive] = useState(false)

  // Simulation & Failure Scenario State (4 Core Scenarios from BACKEND_PLAN.md)
  const [splitComplete, setSplitComplete] = useState(false)
  const [shelterAOverflow, setShelterAOverflow] = useState(true)
  const [isRerouting, setIsRerouting] = useState(false)
  const [rerouteResolved, setRerouteResolved] = useState(false)
  const [waterOnline, setWaterOnline] = useState(true)
  const [toastMessage, setToastMessage] = useState('Vigilio Deployment-Ready Network Synchronized.')

  const showToast = (msg: string) => {
    setToastMessage(msg)
    window.setTimeout(() => setToastMessage(''), 4500)
  }

  const toggleTheme = () => {
    const next = theme === 'light' ? 'dark' : 'light'
    setTheme(next)
    showToast(next === 'dark' ? 'Obsidian Stealth Dark Mode active.' : 'Pale Ecru Sage Light Mode active.')
  }

  // SCENARIO 1: 180-Meal Batch Split (Max 40/rider cap)
  const handleSplitBatch = () => {
    setSplitComplete(true)
    showToast('Scenario 1: 180 Cooked Meals split into 5 sub-tickets (40+40+40+40+20) · 0 Unaccounted.')
  }

  // SCENARIO 2: Ghost Lease Revocation / Volunteer Stall
  const handleStallRider = () => {
    showToast('Scenario 2: Rider #12 lease timer expired (00:00) · Unpicked inventory recovered into pool.')
  }

  // SCENARIO 3: Mid-Journey Shelter Closure & Radar/Map Reroute
  const handleTriggerReroute = () => {
    setIsRerouting(true)
    showToast('Autonomous Reroute: Diverting Courier #07 from Shelter A to Relief Camp B...')
    setTimeout(() => {
      setIsRerouting(false)
      setRerouteResolved(true)
      setShelterAOverflow(false)
      showToast('✓ Reroute Locked: 40 Meals committed to Relief Camp B inside 19m safe buffer!')
    }, 1600)
  }

  // SCENARIO 4: Supply Dependency Guard
  const handleToggleWater = () => {
    const next = !waterOnline
    setWaterOnline(next)
    showToast(
      next
        ? 'Scenario 4: Potable water restored at Shelter C · Raw rations approved for delivery.'
        : 'Scenario 4: Missing clean water at Shelter C · Raw rations dispatch blocked & held at origin.'
    )
  }

  // Quick Dispatch Consignment
  const handleCreateConsignment = (data: any) => {
    showToast(`New Consignment Dispatched: ${data.cargoName} (${data.quantity} units) to ${data.targetShelter}.`)
  }

  // JSON Audit Trace Snapshot Export
  const handleExportAuditLog = () => {
    const auditData = {
      system: 'Vigilio Autonomous Humanitarian Logistics Network',
      exportTimestamp: new Date().toISOString(),
      networkStatus: 'SYNCHRONIZED',
      invariants: {
        conservationOfMass: '180 == sum(allocated_quantities)',
        physicalCustodyProtection: 'ACTIVE',
        cleanWaterDependencyGuard: waterOnline ? 'SATISFIED' : 'BLOCKED',
      },
      scenariosState: {
        splitComplete,
        shelterAOverflow,
        rerouteResolved,
        waterOnline,
      },
      verifiedIncidentsCount: 5,
    }
    const blob = new Blob([JSON.stringify(auditData, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `vigilio-audit-trail-${Date.now()}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    showToast('✓ Forensic Audit Trail exported as JSON.')
  }

  const handleResetSimulation = () => {
    setSplitComplete(false)
    setShelterAOverflow(true)
    setIsRerouting(false)
    setRerouteResolved(false)
    setWaterOnline(true)
    showToast('Simulation scenarios reset to initial operational baseline.')
  }

  return (
    <div className={`cyber-app-wrapper ${theme === 'dark' ? 'is-dark-theme' : ''}`}>
      <div className="cyber-main-frame">
        {/* Top Navigation Bar with All Functional Utilities */}
        <CyberTopNav
          activeTab={activeTab}
          onTabChange={(tab) => {
            setActiveTab(tab)
            setIsMatrixActive(false)
            if (tab === 'map') showToast('Switched to Live Volunteer Fleet & Shelter Map.')
            else if (tab === 'alerts') showToast('Switched to Key Alerts Matrix workspace.')
            else if (tab === 'insights') showToast('Switched to Network Telemetry Insights workspace.')
            else if (tab === 'executions') showToast('Switched to Autonomous Executions Audit workspace.')
            else showToast('Switched to Data Overview workspace.')
          }}
          onOpenAlertsTable={() => setIsAlertsTableOpen(true)}
          onOpenCreateModal={() => setIsCreateModalOpen(true)}
          onOpenFilterDrawer={() => setIsFilterDrawerOpen(true)}
          onToggleOperationsMatrix={() => {
            const next = !isMatrixActive
            setIsMatrixActive(next)
            showToast(next ? 'Opened Integrated Operations Command Grid.' : 'Returned to Dashboard view.')
          }}
          onOpenSettingsModal={() => setIsSettingsModalOpen(true)}
          theme={theme}
          onToggleTheme={toggleTheme}
          isMatrixActive={isMatrixActive}
        />

        {/* If Operations Matrix is active, show the high-density grid */}
        {isMatrixActive ? (
          <OperationsMatrixView
            onClose={() => setIsMatrixActive(false)}
            onSplitBatch={handleSplitBatch}
            onStallRider={handleStallRider}
            onTriggerReroute={handleTriggerReroute}
            onToggleWater={handleToggleWater}
            splitComplete={splitComplete}
            rerouteResolved={rerouteResolved}
            waterOnline={waterOnline}
          />
        ) : (
          <AnimatePresence mode="wait">
            {/* TAB 0: Landing Page (Exact high-motion recreation of landing page.mp4) */}
            {activeTab === 'landing' && (
              <motion.div
                key="tab-landing"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -12 }}
                transition={{ duration: 0.3 }}
              >
                <VigilioLandingPage
                  onEnterDashboard={(tab) => {
                    const target = tab || 'overview'
                    setActiveTab(target)
                    showToast(`Entering Vigilio Mission Control: ${target.toUpperCase()}`)
                  }}
                />
              </motion.div>
            )}

            {/* TAB 1: Data overview (The ONLY place where the dial/speedometer hero stage sits!) */}
            {activeTab === 'overview' && (
              <motion.div
                key="tab-overview"
                className="overview-flow-stack"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.25 }}
              >
                {/* Upper Dark Hero Stage (#181818) */}
                <DarkHeroStage
                  onBackToOverview={() => {
                    setIsRerouting(false)
                    setRerouteResolved(false)
                    setShelterAOverflow(true)
                    showToast('Reset to Master Dynamic View.')
                  }}
                  onTriggerReroute={handleTriggerReroute}
                  shelterAOverflow={shelterAOverflow}
                  isRerouting={isRerouting}
                  rerouteResolved={rerouteResolved}
                  onResolveIncident={(id) => showToast(`Incident ${id} marked managed.`)}
                  onSelectSeverity={(sev) => showToast(`Filtered telemetry to Severity: ${sev}`)}
                  onOpenMap={() => setActiveTab('map')}
                />

                {/* Bottom Bento Row (4 Cards) */}
                <div className="cyber-bottom-grid">
                  {/* Card 1: Sources */}
                  <SourcesBentoCard
                    onSplitBatch={handleSplitBatch}
                    splitComplete={splitComplete}
                  />

                  {/* Card 2: Alerts */}
                  <AlertsBentoCard
                    waterOnline={waterOnline}
                    onToggleWater={handleToggleWater}
                    onOpenAlertsTable={() => setIsAlertsTableOpen(true)}
                  />

                  {/* Card 3: Automation */}
                  <AutomationBentoCard
                    onRunPlaybook1={handleSplitBatch}
                    onRunPlaybook2={handleStallRider}
                    onRunPlaybook3={handleTriggerReroute}
                  />

                  {/* Card 4: Assets */}
                  <AssetsBentoCard
                    onSelectAsset={(id) => showToast(`Selected asset: ${id} · Telemetry active.`)}
                    onOpenFleetMap={() => setActiveTab('map')}
                  />
                </div>

                {/* Bottom Horizontal Floating Timeline Bar */}
                <BottomTimelineBar
                  onOpenFullTimeline={() => setIsTimelineDrawerOpen(true)}
                  onQuickAddAlert={() => setIsCreateModalOpen(true)}
                />
              </motion.div>
            )}

            {/* TAB 2: Live Map ↗ (Swiggy / Zomato order tracking style real-time logistics map) */}
            {activeTab === 'map' && (
              <motion.div
                key="tab-map"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.25 }}
              >
                <LiveFleetMapView
                  onTriggerReroute={handleTriggerReroute}
                  rerouteResolved={rerouteResolved}
                />
              </motion.div>
            )}

            {/* TAB 3: Key Alerts (Dedicated Incident Operations Center) */}
            {activeTab === 'alerts' && (
              <motion.div
                key="tab-alerts"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.25 }}
              >
                <KeyAlertsView
                  onTriggerReroute={handleTriggerReroute}
                  rerouteResolved={rerouteResolved}
                  waterOnline={waterOnline}
                  onToggleWater={handleToggleWater}
                  onOpenAlertsTable={() => setIsAlertsTableOpen(true)}
                />
              </motion.div>
            )}

            {/* TAB 4: Insights (Dedicated Spoilage Risk Curves & Network Telemetry) */}
            {activeTab === 'insights' && (
              <motion.div
                key="tab-insights"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.25 }}
              >
                <InsightsView />
              </motion.div>
            )}

            {/* TAB 5: Executions (Dedicated Autonomous Playbooks & Audit Ledger) */}
            {activeTab === 'executions' && (
              <motion.div
                key="tab-executions"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.25 }}
              >
                <ExecutionsView
                  onRunPlaybook1={handleSplitBatch}
                  onRunPlaybook2={handleStallRider}
                  onRunPlaybook3={handleTriggerReroute}
                  onToggleWater={handleToggleWater}
                  splitComplete={splitComplete}
                  rerouteResolved={rerouteResolved}
                  waterOnline={waterOnline}
                />
              </motion.div>
            )}
          </AnimatePresence>
        )}
      </div>

      {/* Modals & Drawers */}
      <AlertsTableModal
        isOpen={isAlertsTableOpen}
        onClose={() => setIsAlertsTableOpen(false)}
        onResolve={(id) => {
          showToast(`Incident ${id} transactionally resolved & verified.`)
        }}
      />

      <FullTimelineDrawer
        isOpen={isTimelineDrawerOpen}
        onClose={() => setIsTimelineDrawerOpen(false)}
      />

      <QuickCreateModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onCreateConsignment={handleCreateConsignment}
      />

      <TelemetryFilterDrawer
        isOpen={isFilterDrawerOpen}
        onClose={() => setIsFilterDrawerOpen(false)}
        onApplyFilters={(filters) => {
          showToast(`Parameters applied: Buffer ${filters.bioWindowBuffer}m, Cap ${filters.courierWeightCap} meals.`)
        }}
      />

      <SystemSettingsModal
        isOpen={isSettingsModalOpen}
        onClose={() => setIsSettingsModalOpen(false)}
        onExportAuditLog={handleExportAuditLog}
        onResetSimulation={handleResetSimulation}
      />

      {/* Toast Notification */}
      {toastMessage && (
        <div className="toast">
          <span className="toast-dot" style={{ backgroundColor: '#F9771D' }} />
          <span>{toastMessage}</span>
        </div>
      )}
    </div>
  )
}
export default App
