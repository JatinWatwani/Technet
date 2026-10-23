import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { VigiloProvider, useVigilo } from './context/VigiloContext'
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

function VigiloDashboard() {
  const [activeTab, setActiveTab] = useState('overview')
  const [theme, setTheme] = useState<'light' | 'dark'>('light')
  const [isAlertsTableOpen, setIsAlertsTableOpen] = useState(false)
  const [isTimelineDrawerOpen, setIsTimelineDrawerOpen] = useState(false)
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [isFilterDrawerOpen, setIsFilterDrawerOpen] = useState(false)
  const [isSettingsModalOpen, setIsSettingsModalOpen] = useState(false)
  const [isMatrixActive, setIsMatrixActive] = useState(false)
  const [toastMessage, setToastMessage] = useState('Vigilo Autonomous Humanitarian Logistics Network Synchronized.')

  const {
    batches,
    riders,
    shelters,
    allocations,
    deliveries,
    incidents,
    metrics,
    clock,
    events,
    presets,
    baselineReport,
    isBackendLive,
    splitComplete,
    shelterAOverflow,
    isRerouting,
    rerouteResolved,
    waterOnline,
    splitOversizedBatch,
    recoverGhostLease,
    triggerReroute,
    toggleWaterPrerequisite,
    createConsignment,
    resolveIncident,
    advanceTime,
    resetSimulation,
    runPresetBenchmark,
  } = useVigilo()

  const showToast = (msg: string) => {
    setToastMessage(msg)
    window.setTimeout(() => setToastMessage(''), 4500)
  }

  const toggleTheme = () => {
    const next = theme === 'light' ? 'dark' : 'light'
    setTheme(next)
    showToast(next === 'dark' ? 'Obsidian Stealth Dark Mode active.' : 'Pale Ecru Sage Light Mode active.')
  }

  // SCENARIO 1: 180-Meal Batch Split
  const handleSplitBatch = async () => {
    const res = await splitOversizedBatch()
    showToast(res)
  }

  // SCENARIO 2: Ghost Lease Revocation / Volunteer Stall
  const handleStallRider = async () => {
    const res = await recoverGhostLease()
    showToast(res)
  }

  // SCENARIO 3: Mid-Journey Shelter Closure & Radar/Map Reroute
  const handleTriggerReroute = async () => {
    showToast('Autonomous Reroute: Calculating bio-safe alternative destination...')
    const res = await triggerReroute()
    showToast(res)
  }

  // SCENARIO 4: Supply Dependency Guard
  const handleToggleWater = async () => {
    const res = await toggleWaterPrerequisite()
    showToast(res)
  }

  // Quick Dispatch Consignment
  const handleCreateConsignment = async (data: any) => {
    const res = await createConsignment(data)
    showToast(res)
  }

  // Advance Time sweep
  const handleAdvanceClock = async (mins: number) => {
    await advanceTime(mins)
    showToast(`Simulation clock advanced +${mins}m. Heartbeat lease sweep completed.`)
  }

  // JSON Audit Trace Snapshot Export
  const handleExportAuditLog = () => {
    const auditData = {
      system: 'Vigilo Autonomous Humanitarian Logistics Network',
      exportTimestamp: new Date().toISOString(),
      networkStatus: isBackendLive ? 'CONNECTED_LIVE' : 'OFFLINE_STANDALONE',
      authoritativeClock: clock,
      systemMetrics: metrics,
      invariants: {
        conservationOfMass: 'sum(allocated_quantities) == sum(batch_original_quantities)',
        massConservationViolations: metrics?.ledger_reconciliation_healthy ? 0 : 1,
        physicalCustodyProtection: 'ACTIVE',
        cleanWaterDependencyGuard: waterOnline ? 'SATISFIED' : 'BLOCKED',
      },
      liveBatchesCount: batches.length,
      liveRidersCount: riders.length,
      liveSheltersCount: shelters.length,
      liveAllocationsCount: allocations.length,
      liveDeliveriesCount: deliveries.length,
      verifiedIncidentsCount: incidents.length,
      scenariosState: {
        splitComplete,
        shelterAOverflow,
        rerouteResolved,
        waterOnline,
      },
      operationalAuditEvents: events.slice(0, 50),
    }
    const blob = new Blob([JSON.stringify(auditData, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `vigilo-audit-trail-${Date.now()}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    showToast('✓ Forensic Audit Trail & Invariant State exported as JSON.')
  }

  const handleResetSimulation = async () => {
    await resetSimulation()
    showToast('Simulation state & database seed reset to initial baseline.')
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
            if (tab === 'landing') showToast('Switched to Vigilio Home.')
            else if (tab === 'map') showToast('Switched to Live Volunteer Fleet & Shelter Map.')
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
          isBackendLive={isBackendLive}
          clockTime={clock?.current_time}
          onAdvanceTime={handleAdvanceClock}
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
            {/* TAB 0: Landing Page */}
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

            {/* TAB 1: Data overview */}
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
                    showToast('Reset to Master Dynamic View.')
                  }}
                  onTriggerReroute={handleTriggerReroute}
                  shelterAOverflow={shelterAOverflow}
                  isRerouting={isRerouting}
                  rerouteResolved={rerouteResolved}
                  onResolveIncident={async (id) => {
                    await resolveIncident(id)
                    showToast(`Incident ${id} marked managed.`)
                  }}
                  onSelectSeverity={(sev) => showToast(`Filtered telemetry to Severity: ${sev}`)}
                  onOpenMap={() => setActiveTab('map')}
                  incidents={incidents}
                />

                {/* Bottom Bento Row (4 Cards) */}
                <div className="cyber-bottom-grid">
                  {/* Card 1: Sources */}
                  <SourcesBentoCard
                    onSplitBatch={handleSplitBatch}
                    splitComplete={splitComplete}
                    batches={batches}
                  />

                  {/* Card 2: Alerts */}
                  <AlertsBentoCard
                    waterOnline={waterOnline}
                    onToggleWater={handleToggleWater}
                    onOpenAlertsTable={() => setIsAlertsTableOpen(true)}
                    incidents={incidents}
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
                    riders={riders}
                  />
                </div>

                {/* Bottom Horizontal Floating Timeline Bar */}
                <BottomTimelineBar
                  onOpenFullTimeline={() => setIsTimelineDrawerOpen(true)}
                  onQuickAddAlert={() => setIsCreateModalOpen(true)}
                />
              </motion.div>
            )}

            {/* TAB 2: Live Map */}
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
                  shelters={shelters}
                  riders={riders}
                />
              </motion.div>
            )}

            {/* TAB 3: Key Alerts */}
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

            {/* TAB 4: Insights */}
            {activeTab === 'insights' && (
              <motion.div
                key="tab-insights"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.25 }}
              >
                <InsightsView metrics={metrics} shelters={shelters} />
              </motion.div>
            )}

            {/* TAB 5: Executions */}
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
                  events={events}
                  baselineReport={baselineReport}
                  presets={presets}
                  onRunBenchmark={runPresetBenchmark}
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
        onResolve={async (id) => {
          await resolveIncident(id)
          showToast(`Incident ${id} transactionally resolved & verified.`)
        }}
        incidents={incidents}
      />

      <FullTimelineDrawer
        isOpen={isTimelineDrawerOpen}
        onClose={() => setIsTimelineDrawerOpen(false)}
      />

      <QuickCreateModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onCreateConsignment={handleCreateConsignment}
        shelters={shelters}
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

export function App() {
  return (
    <VigiloProvider>
      <VigiloDashboard />
    </VigiloProvider>
  )
}

export default App
