import { HeroKpiRow } from '../chaos-ember/HeroKpiRow'
import { SafeDecisionGauge } from '../chaos-ember/SafeDecisionGauge'
import { OrangeRecoveryCard } from '../chaos-ember/OrangeRecoveryCard'
import { AuditTraceStack } from '../chaos-ember/AuditTraceStack'
import { MiniRouteMapCard } from '../chaos-ember/MiniRouteMapCard'
import { FloatingIncidentModal } from '../chaos-ember/FloatingIncidentModal'
import type { FeedEvent } from '../../types'

interface ChaosViewProps {
  events: FeedEvent[]
  incidentOpen: boolean
  onInject: (type?: string) => void
  onCloseIncident: () => void
  onVerifyIncident?: () => void
}

export function ChaosView({
  events,
  incidentOpen,
  onInject,
  onCloseIncident,
  onVerifyIncident,
}: ChaosViewProps) {
  return (
    <div className="chaos-layout view-transition">
      <HeroKpiRow />

      <div className="chaos-grid">
        <SafeDecisionGauge onInject={onInject} />

        <OrangeRecoveryCard onInject={() => onInject('general')} />

        <AuditTraceStack events={events} />

        <MiniRouteMapCard />
      </div>

      <FloatingIncidentModal
        isOpen={incidentOpen}
        onClose={onCloseIncident}
        onVerify={onVerifyIncident}
      />
    </div>
  )
}
