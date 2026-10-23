// Vigilo Authoritative Backend API Client

const API_BASE = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000'

export interface ItemRules {
  safe_handling_minutes: number
  safety_buffer_minutes: number
  required_prerequisites: string[]
  storage_requirement: string
}

export interface Batch {
  id: string
  donor_id: string
  item_type: string
  original_quantity: number
  available_quantity: number
  reserved_quantity: number
  picked_up_quantity: number
  delivered_quantity: number
  spoiled_quantity: number
  item_rules: ItemRules
  created_at: string
  safe_until: string
}

export interface GeoLocation {
  latitude: number
  longitude: number
}

export interface Rider {
  id: string
  user_id: string
  capacity: number
  active_load: number
  remaining_capacity: number
  available: boolean
  status: 'AVAILABLE' | 'IN_TRANSIT' | 'OFFLINE' | 'SUSPENDED'
  location: GeoLocation | null
  last_heartbeat_at: string | null
}

export interface ReceivingHours {
  open_hour: number
  close_hour: number
}

export interface Shelter {
  id: string
  name: string
  demand_remaining: number
  receiving_capacity_remaining: number
  prerequisites: string[]
  open: boolean
  status: 'OPEN' | 'CLOSED' | 'OVER_CAPACITY' | 'EVACUATING'
  location: GeoLocation | null
  receiving_hours: ReceivingHours
}

export interface Allocation {
  id: string
  batch_id: string
  rider_id: string
  shelter_id: string
  quantity: number
  travel_minutes: number
  handoff_minutes: number
  state: 'CLAIMED' | 'ACKNOWLEDGED' | 'PICKED_UP' | 'CANCELLED' | 'EXPIRED'
  claimed_at: string
  lease_expires_at: string | null
  safe_until: string
  acknowledged_at: string | null
  picked_up_at: string | null
}

export interface Delivery {
  id: string
  allocation_id: string
  batch_id: string
  rider_id: string
  current_shelter_id: string
  quantity: number
  state: 'PICKED_UP' | 'IN_TRANSIT' | 'REROUTE_PENDING' | 'DELIVERED' | 'INCIDENT_REVIEW'
  picked_up_at: string
  delivered_at: string | null
  current_location: GeoLocation | null
  destination_history: string[]
}

export interface Incident {
  id: string
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  status: 'REPORTED' | 'INVESTIGATING' | 'ESCALATED' | 'RESOLVED'
  affected_entity_type: string
  affected_entity_id: string
  reason_code: string
  description: string
  created_at: string
  resolved_at: string | null
  evidence: Record<string, any>
}

export interface SystemMetrics {
  system_status: string
  uptime_seconds: number
  batches_count: number
  riders_total: number
  riders_available: number
  riders_in_transit: number
  shelters_total: number
  shelters_open: number
  allocations_active: number
  deliveries_in_transit: number
  deliveries_completed: number
  inventory_available_units: number
  inventory_reserved_units: number
  inventory_in_transit_units: number
  inventory_delivered_units: number
  inventory_spoiled_units: number
  incidents_total: number
  incidents_active: number
  outbox_pending_messages: number
  audit_records_total: number
  ledger_reconciliation_healthy: boolean
}

export interface ClockState {
  current_time: string
  iso: string
  clock_type: string
}

export interface OperationalEvent {
  id: string
  event_type: string
  aggregate_id: string
  aggregate_type: string
  occurred_at: string
  payload: Record<string, any>
  actor: string
  evidence: Record<string, any>
}

export interface ScenarioPreset {
  preset_id: string
  name: string
  description: string
  difficulty: string
  chaos_elements: string[]
}

export interface BaselineScorecardItem {
  metric_name: string
  vigilo_value: string | number
  baseline_value: string | number
  improvement: string
  passed_invariant: boolean
}

export interface BaselineComparisonReport {
  scenario_id: string
  scenario_name: string
  seed: number
  vigilo_metrics: Record<string, any>
  baseline_metrics: Record<string, any>
  comparative_scorecard: BaselineScorecardItem[]
  verdict_summary: string
}

class VigiloApiClient {
  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${API_BASE}${endpoint}`
    const headers = {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    }

    const response = await fetch(url, { ...options, headers })
    if (!response.ok) {
      let errorData: any
      try {
        errorData = await response.json()
      } catch {
        errorData = { message: `HTTP ${response.status}: ${response.statusText}` }
      }
      const err = new Error(errorData.detail?.message || errorData.detail || errorData.message || 'API request failed')
      ;(err as any).status = response.status
      ;(err as any).data = errorData
      throw err
    }
    return response.json()
  }

  // Liveness & Readiness
  async getHealth(): Promise<{ status: string }> {
    return this.request<{ status: string }>('/v1/health')
  }

  async getReadiness(): Promise<any> {
    return this.request<any>('/v1/ready')
  }

  async getMetrics(): Promise<SystemMetrics> {
    return this.request<SystemMetrics>('/v1/metrics')
  }

  // Clock & State Seeding
  async getClock(): Promise<ClockState> {
    return this.request<ClockState>('/v1/clock')
  }

  async advanceClock(minutes: number): Promise<ClockState> {
    return this.request<ClockState>('/v1/clock/advance', {
      method: 'POST',
      body: JSON.stringify({ minutes, seconds: 0 }),
    })
  }

  async resetSeed(): Promise<any> {
    return this.request<any>('/v1/seed', { method: 'POST' })
  }

  // Batches & Inventory
  async getBatches(): Promise<Batch[]> {
    return this.request<Batch[]>('/v1/batches')
  }

  async createBatch(payload: {
    donor_id: string
    item_type: string
    quantity: number
    safe_handling_minutes?: number
    safety_buffer_minutes?: number
    required_prerequisites?: string[]
    storage_requirement?: string
  }): Promise<Batch> {
    return this.request<Batch>('/v1/batches', {
      method: 'POST',
      body: JSON.stringify({
        donor_id: payload.donor_id,
        item_type: payload.item_type,
        quantity: payload.quantity,
        item_rules: {
          safe_handling_minutes: payload.safe_handling_minutes ?? 180,
          safety_buffer_minutes: payload.safety_buffer_minutes ?? 15,
          required_prerequisites: payload.required_prerequisites ?? [],
          storage_requirement: payload.storage_requirement ?? 'AMBIENT',
        },
      }),
    })
  }

  async getBatchHistory(batchId: string): Promise<any> {
    return this.request<any>(`/v1/audit/inventory/${batchId}`)
  }

  // Riders
  async getRiders(): Promise<Rider[]> {
    return this.request<Rider[]>('/v1/riders')
  }

  async updateRiderStatus(riderId: string, status: string): Promise<Rider> {
    return this.request<Rider>(`/v1/riders/${riderId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    })
  }

  // Shelters
  async getShelters(): Promise<Shelter[]> {
    return this.request<Shelter[]>('/v1/shelters')
  }

  async updateShelterDemand(shelterId: string, demand_remaining: number): Promise<Shelter> {
    return this.request<Shelter>(`/v1/shelters/${shelterId}/demand`, {
      method: 'PATCH',
      body: JSON.stringify({ demand_remaining }),
    })
  }

  async closeShelter(shelterId: string, reason?: string, autoReroute = true): Promise<Shelter> {
    return this.request<Shelter>(`/v1/shelters/${shelterId}/close`, {
      method: 'POST',
      headers: { 'X-Actor-Role': 'ADMIN' },
      body: JSON.stringify({ reason: reason || 'Facility closed due to operational conditions', auto_reroute: autoReroute }),
    })
  }

  async reopenShelter(shelterId: string): Promise<Shelter> {
    return this.request<Shelter>(`/v1/shelters/${shelterId}/reopen`, {
      method: 'POST',
      headers: { 'X-Actor-Role': 'ADMIN' },
    })
  }

  // Dispatch & Allocations
  async getCandidateSplit(batchId: string): Promise<any> {
    return this.request<any>(`/v1/dispatch/candidates/${batchId}`)
  }

  async previewDispatch(payload: {
    batch_id: string
    rider_id: string
    shelter_id: string
    quantity: number
    travel_minutes?: number
    handoff_minutes?: number
  }): Promise<any> {
    return this.request<any>('/v1/dispatch/preview', {
      method: 'POST',
      body: JSON.stringify({
        travel_minutes: 25,
        handoff_minutes: 10,
        ...payload,
      }),
    })
  }

  async commitDispatch(payload: {
    batch_id: string
    rider_id: string
    shelter_id: string
    quantity: number
    travel_minutes?: number
    handoff_minutes?: number
  }): Promise<{ allocation_id: string }> {
    return this.request<{ allocation_id: string }>('/v1/dispatch/commit', {
      method: 'POST',
      body: JSON.stringify({
        travel_minutes: 25,
        handoff_minutes: 10,
        ...payload,
      }),
    })
  }

  async getAllocations(): Promise<Allocation[]> {
    return this.request<Allocation[]>('/v1/allocations')
  }

  async acknowledgeAllocation(allocationId: string): Promise<Allocation> {
    return this.request<Allocation>(`/v1/allocations/${allocationId}/acknowledge`, {
      method: 'POST',
      headers: { 'X-Actor-Role': 'RIDER' },
    })
  }

  async pickupAllocation(allocationId: string): Promise<Delivery> {
    return this.request<Delivery>(`/v1/allocations/${allocationId}/pickup`, {
      method: 'POST',
      headers: { 'X-Actor-Role': 'RIDER' },
    })
  }

  async deliverCargo(deliveryId: string): Promise<Delivery> {
    return this.request<Delivery>(`/v1/deliveries/${deliveryId}/deliver`, {
      method: 'POST',
      headers: { 'X-Actor-Role': 'RIDER' },
    })
  }

  async cancelAllocation(allocationId: string, reason = 'Operator cancellation'): Promise<any> {
    return this.request<any>(`/v1/allocations/${allocationId}/cancel`, {
      method: 'POST',
      headers: { 'X-Actor-Role': 'ADMIN' },
      body: JSON.stringify({ reason }),
    })
  }

  // Deliveries & In-Transit Reroutes
  async getDeliveries(): Promise<Delivery[]> {
    return this.request<Delivery[]>('/v1/deliveries')
  }

  async previewReroute(deliveryId: string): Promise<any> {
    return this.request<any>(`/v1/deliveries/${deliveryId}/reroute/preview`, {
      method: 'POST',
    })
  }

  async commitReroute(deliveryId: string, targetShelterId?: string, reason = 'In-transit reroute'): Promise<Delivery> {
    return this.request<Delivery>(`/v1/deliveries/${deliveryId}/reroute/commit`, {
      method: 'POST',
      headers: { 'X-Actor-Role': 'ADMIN' },
      body: JSON.stringify({ target_shelter_id: targetShelterId, reason }),
    })
  }

  // Incidents
  async getIncidents(): Promise<Incident[]> {
    return this.request<Incident[]>('/v1/incidents')
  }

  async resolveIncident(incidentId: string, notes = 'Resolved by operator'): Promise<Incident> {
    return this.request<Incident>(`/v1/incidents/${incidentId}/resolve`, {
      method: 'POST',
      body: JSON.stringify({ resolution_notes: notes }),
    })
  }

  async escalateIncident(incidentId: string, reason = 'Escalated for immediate review'): Promise<Incident> {
    return this.request<Incident>(`/v1/incidents/${incidentId}/escalate`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    })
  }

  // Autonomous Sweeps
  async runSweeps(): Promise<any> {
    return this.request<any>('/v1/workers/run-sweeps', {
      method: 'POST',
    })
  }

  // Audit Events
  async getEvents(limit = 50): Promise<OperationalEvent[]> {
    return this.request<OperationalEvent[]>(`/v1/events?limit=${limit}`)
  }

  // Simulation & Chaos Lab
  async getScenarioPresets(): Promise<ScenarioPreset[]> {
    return this.request<ScenarioPreset[]>('/v1/scenarios/presets')
  }

  async createScenario(payload: {
    name: string
    preset_id?: string
    scenario_id?: string
    seed?: number
    description?: string
  }): Promise<any> {
    return this.request<any>('/v1/scenarios', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  }

  async advanceScenarioTime(scenarioId: string, minutes: number): Promise<any> {
    return this.request<any>(`/v1/scenarios/${scenarioId}/advance-time`, {
      method: 'POST',
      body: JSON.stringify({ minutes }),
    })
  }

  async injectScenarioFailure(scenarioId: string, failureType: string, targetId: string, params: Record<string, any> = {}): Promise<any> {
    return this.request<any>(`/v1/scenarios/${scenarioId}/inject-failure`, {
      method: 'POST',
      body: JSON.stringify({ failure_type: failureType, target_id: targetId, params }),
    })
  }

  async getScenarioState(scenarioId: string): Promise<any> {
    return this.request<any>(`/v1/scenarios/${scenarioId}/state`)
  }

  async getScenarioReplay(scenarioId: string): Promise<any> {
    return this.request<any>(`/v1/scenarios/${scenarioId}/replay`)
  }

  async compareScenarioBaseline(scenarioId: string): Promise<BaselineComparisonReport> {
    return this.request<BaselineComparisonReport>(`/v1/scenarios/${scenarioId}/compare-baseline`, {
      method: 'POST',
    })
  }

  // Emergency Override
  async executeEmergencyOverride(payload: {
    override_type: string
    target_entity_type: string
    target_entity_id: string
    justification: string
    authorized_by: string
    params?: Record<string, any>
  }): Promise<any> {
    return this.request<any>('/v1/emergency/override', {
      method: 'POST',
      headers: { 'X-Actor-Role': 'ADMIN' },
      body: JSON.stringify(payload),
    })
  }
}

export const api = new VigiloApiClient()
