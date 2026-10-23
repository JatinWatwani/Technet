# Vigilo — Resilience-Aware Humanitarian Logistics Engine

Vigilo is a production-grade, authoritative backend engine engineered for crisis-zone donation routing, cold-chain preservation, and autonomous self-healing recovery under compounding disasters (urban floods, sudden shelter closures, rider breakdown, and communication loss).

---

## 🏛️ Architectural Overview & Core Invariants

Vigilo is structured strictly on resilient distributed systems principles:

1. **Double-Entry Inventory Ledger (Immutable)**:
   - Every gram/unit of intake is conserved: `available + reserved + picked_up + delivered + spoiled = total_batch_quantity`.
   - Double allocations are physically impossible; concurrent claims compete using row-level locking or atomic leases.
   - Picked-up cargo is in transit custody and **can never be cancelled or released back into available inventory**.

2. **Last-Safe-Decision Clock & Constraint Engine**:
   - Dynamic feasibility engine computing hard constraints: weight/volume capacity, storage compatibility (ambient vs cold chain), receiving hours, transit travel time, handoff durations, and flood corridor passability.
   - Proactive safety clock alerting operations *before* safe-handling margins elapse.

3. **Autonomous Recovery Engine & Sweep Workers**:
   - **Reservation Expiration Worker**: Sweeps unacknowledged claims past lease expiry, atomically restoring unpicked inventory to available stock.
   - **Heartbeat & Telemetry Monitor**: Tracks rider connectivity, escalates to incidents if telemetry drops.
   - **Cascading Shelter Closure**: Automatically cascades facility closures, recovers unpicked claims, and reroutes in-transit cargo to scored backup destinations with open receiving hours and matching storage prerequisites.

4. **Simulation Engine & Chaos Lab**:
   - Isolated, accelerated simulated universe running preset judge scenarios (`oversized_donation_split`, `ghost_reservation`, `in_transit_shelter_closure`, `cascading_flood_disruption`).
   - Deterministic event replay tape recording all decisions, audit trails, and failure injections.
   - **Greedy Baseline Comparison**: Compares Vigilo side-by-side against naive nearest-feasible dispatchers, generating comparative scorecards on delivery completion, spoilage prevention, and recovery success.

5. **Operational Telemetry & Observability**:
   - `/v1/ready`: Multi-subsystem readiness probe (clock, storage, ledger reconciliation, workers).
   - `/v1/metrics`: Structured JSON & Prometheus exposition format (`text/plain; version=0.0.4`).
   - `/v1/events` & `/v1/audit/decisions/{id}`: Verifiable event log and decision explanation records.
   - `/v1/emergency/override`: Audited, role-gated (`ADMIN`) emergency override mechanism.

---

## 🚀 Quickstart & Clean Environment Setup

### 1. Requirements
- Python 3.11+ (tested on Python 3.13)
- Optional: PostgreSQL / Supabase connection (falls back to isolated in-memory domain service for local development and testing)

### 2. Installation
```bash
git clone https://github.com/JatinWatwani/Technet.git
cd Technet
python -m pip install -e ".[dev]"
```

### 3. Environment Variables
Create a `.env` file in the root directory:
```env
# Operational environment
VIGILO_ENV=production
CLOCK_MODE=SIMULATED        # Options: SIMULATED (for deterministic tests) or SYSTEM (wall-clock)

# Database (optional - if omitted, memory domain backend runs)
DATABASE_URL=postgresql://user:password@localhost:5432/vigilo
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SECRET_KEY=your-service-role-key
```

### 4. Run the Full Test Suite
Execute the 87 automated tests across all 7 development phases:
```bash
python -m pytest -v
```

### 5. Launch the API Server
```bash
uvicorn vigilo.main:app --app-dir apps/api --host 0.0.0.0 --port 8000 --reload
```
Interactive API documentation is accessible at: `http://localhost:8000/docs`

---

## 📡 Key API Endpoints

### 🩺 Health & Observability
- `GET /v1/health`: Liveness probe.
- `GET /v1/ready`: Readiness probe verifying ledger reconciliation and worker status.
- `GET /v1/metrics`: Prometheus metrics (`format=prometheus` or `Accept: text/plain`) or structured JSON.

### 📦 Dispatch & Execution
- `POST /v1/dispatch/preview`: Feasibility check, candidate discovery, and Last-Safe-Decision clock calculation.
- `POST /v1/dispatch/commit`: Creates an atomic allocation claim with a lease expiration.
- `POST /v1/allocations/{id}/acknowledge`: Rider confirms acceptance.
- `POST /v1/allocations/{id}/pickup`: Confirms physical pickup (cargo enters physical transit custody).
- `POST /v1/deliveries/{id}/deliver`: Confirms safe delivery at destination shelter.
- `POST /v1/allocations/{id}/cancel`: Cancels unpicked allocation and restores available batch balance.

### 🚨 Recovery Engine & Workers
- `POST /v1/shelters/{id}/close`: Cascades shelter shutdown, releases unpicked claims, and reroutes active deliveries.
- `POST /v1/deliveries/{id}/reroute/preview`: Scores alternative destinations for in-transit cargo.
- `POST /v1/deliveries/{id}/reroute/commit`: Updates destination shelter to chosen target.
- `POST /v1/workers/run-sweeps`: Autonomous worker executing lease expiration, heartbeat monitoring, and safety-deadline checks.
- `POST /v1/incidents/{id}/resolve`: Resolves an incident with operational notes.

### 🧪 Simulation Studio & Chaos Lab
- `GET /v1/scenarios/presets`: Lists judge evaluation presets.
- `POST /v1/scenarios`: Creates an isolated scenario sandbox.
- `POST /v1/scenarios/{id}/advance-time`: Advances simulated clock and triggers background sweep workers.
- `POST /v1/scenarios/{id}/inject-failure`: Injects real-time failures (`SHELTER_CLOSURE`, `RIDER_FAILURE`, `FLOOD_DISRUPTION`).
- `GET /v1/scenarios/{id}/replay`: Replays chronological sequence of decisions and events.
- `POST /v1/scenarios/{id}/compare-baseline`: Runs Greedy Baseline and generates comparative scorecard.

### 🛡️ Auditing & Emergency Overrides
- `GET /v1/events`: Chronological domain event log.
- `GET /v1/audit/decisions/{id}`: Full decision record with constraints, evaluated candidates, and actor context.
- `GET /v1/audit/inventory/{batch_id}`: Verifiable ledger timeline and balance history.
- `POST /v1/emergency/override`: Admin-authorized emergency override with mandatory justification and audit trail.

---

## 🧪 Chaos Lab Scenarios

| Scenario ID | Name | Focus & Key Chaos Invariant |
|---|---|---|
| `oversized_donation_split` | Oversized Donation Split | 180kg batch coordinated across multiple cargo bikes and shelters without exceeding vehicle or shelter capacity. |
| `ghost_reservation` | Ghost Reservation Recovery | Rider claims allocation and drops communication; worker sweeps expired lease and restores stock before spoilage. |
| `in_transit_shelter_closure` | In-Transit Shelter Closure | Generator outage at recipient shelter while cold-chain antibiotics are in transit; rerouted to alternative cold storage. |
| `cascading_flood_disruption` | Cascading Urban Flood | Flash flooding submerges transit corridors and closes facilities; verifies clean escalation and 0 cargo lost. |

---

## 📜 Invariant Verification Guarantee
Under all tested crisis scenarios:
- **Quantity Conservation**: Conserved 100% of the time across all transactions.
- **Double Allocation**: 0 violations.
- **Physical Custody**: Cargo in transit is never dumped into available stock or dropped without explicit incident escalation.
- **Spoilage**: 0 units spoiled under Vigilo autonomous recovery.
