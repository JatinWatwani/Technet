import { BatchSplitQueue } from '../live-ops/BatchSplitQueue'
import { SpoilageSplineChart } from '../live-ops/SpoilageSplineChart'
import { LeaseHeartbeatList } from '../live-ops/LeaseHeartbeatList'
import { ShelterReadinessCard } from '../live-ops/ShelterReadinessCard'
import { PrerequisiteRuleCards } from '../dependency-library/PrerequisiteRuleCards'
import type { Batch, Lease, Shelter } from '../../types'

interface LiveViewProps {
  batches: Batch[]
  leases: Lease[]
  shelters: Shelter[]
  waterOnline: boolean
  splitComplete: boolean
  onCreateSplit: () => void
  onStallRider: () => void
  onCloseShelter: () => void
  onToggleWater: () => void
}

export function LiveView({
  batches,
  leases,
  shelters,
  waterOnline,
  splitComplete,
  onCreateSplit,
  onStallRider,
  onCloseShelter,
  onToggleWater,
}: LiveViewProps) {
  return (
    <div className="live-layout view-transition">
      <BatchSplitQueue
        batches={batches}
        splitComplete={splitComplete}
        onCreateSplit={onCreateSplit}
      />

      <SpoilageSplineChart />

      <LeaseHeartbeatList
        leases={leases}
        onStallRider={onStallRider}
      />

      <ShelterReadinessCard
        shelters={shelters}
        waterOnline={waterOnline}
        onCloseShelter={onCloseShelter}
        onToggleWater={onToggleWater}
      />

      <PrerequisiteRuleCards />
    </div>
  )
}
