# Vigilo Backend Plan
## Resilience-Aware Humanitarian Logistics Engine

## 1. Purpose and Scope

This plan covers the backend only. The backend is the authoritative system for inventory, feasibility, dispatch, recovery, safety validation, simulation, auditability, and operational APIs.

The backend must be able to determine one of two outcomes for every dispatch or recovery request:

1. Commit a feasible, safe, transactionally consistent decision.
2. Refuse or escalate the request with a precise reason and preserved inventory state.

The backend must never rely on frontend validation for safety, inventory correctness, authorization, or concurrency protection.

### Out of scope for this plan

- Web pages and frontend components
- Mobile UI implementation
- Visual map rendering
- Frontend state management
- Design systems and styling
- Client-side dispatch logic

Client applications may be added later, but they will consume the backend APIs and events defined here.

## 2. Backend Goals

The backend will provide:

- Quantity-conserving inventory management
- Constraint-based assignment and dispatch
- Reservation leases and acknowledgement deadlines
- Safe recovery of abandoned unpicked allocations
- Controlled rerouting of picked-up and in-transit cargo
- Shelter, rider, donor, and inventory state management
- Safety, compatibility, prerequisite, and deadline checks
- Deterministic simulation with accelerated time
- Concurrency-safe operations
- Append-only operational evidence and audit history
- Baseline-versus-resilience-aware evaluation
- APIs and background workers suitable for future clients

## 3. Recommended Backend Architecture

### Runtime and API

- Python 3.12+
- FastAPI
- Pydantic v2 for request, response, and domain validation
- Uvicorn for local and production ASGI serving
- REST APIs with OpenAPI documentation
- WebSocket or server-sent event publication for operational updates
- Shared typed schemas between API handlers and domain services

### Persistence

- Supabase project `https://gryfvlipyoxdxhllmbqc.supabase.co`
- PostgreSQL as the source of truth through Supabase
- PostGIS for locations, distances, and route-related queries
- Supabase Python client for API access from the backend
- PostgreSQL functions and row locks for transactional allocation and recovery
- SQLAlchemy 2.x with async database support where direct database access is needed
- Alembic or Supabase SQL migrations under version control
- Transactional inventory ledger
- Optimistic version numbers, row-level locks, and database constraints for concurrency control
- Append-only event and audit tables
- Server-only `SUPABASE_SECRET_KEY`; never expose it to a frontend or commit it

### Background processing

- Redis-backed durable job queue using Celery, Dramatiq, or an equivalent worker system
- Reservation-expiration worker
- Rider heartbeat and acknowledgement monitor
- Safety-deadline monitor
- Recovery worker
- Event-outbox publisher
- Simulation clock worker

### Optimization and simulation

- Deterministic Python domain services shared by live operations and simulation
- OR-Tools only when measured workloads justify a solver
- Hypothesis for property-based and invariant testing
- NumPy or pandas only for evaluation and reporting workloads where useful

### Core modules

```text
apps/
  api/
  workers/
packages/
  shared-schemas/
  domain-model/
  inventory-ledger/
  dispatch-engine/
  safety-engine/
  recovery-engine/
  simulation-engine/
  route-provider/
  audit-events/
  authorization/
database/
  migrations/
  seeds/
tests/
  unit/
  integration/
  concurrency/
  scenarios/
```

The dispatch, safety, and recovery modules must be usable by both live operations and simulation. Simulation must not fork a second implementation of the operational rules.

## 4. Backend Domain Model

### Core entities

- `users`: identity and system roles
- `donors`: donation sources
- `batches`: donated supplies and item-level rules
- `inventory_ledger_entries`: immutable quantity movements
- `riders`: capacity, availability, location, and operational status
- `shelters`: demand, receiving capacity, operating hours, and readiness
- `allocations`: quantities reserved for a rider and destination
- `claims`: time-limited ownership of unpicked allocations
- `deliveries`: physical custody and delivery lifecycle
- `route_plans`: travel estimates, route alternatives, and uncertainty
- `dependency_rules`: prerequisites and eligibility requirements
- `incidents`: failures, severity, escalation, and resolution
- `operational_events`: domain events for reconstruction and notifications
- `audit_records`: actor, input, decision, evidence, and outcome
- `scenarios`: deterministic simulation configuration
- `simulation_snapshots`: state snapshots and replay checkpoints
- `idempotency_keys`: safe retry handling for mutating requests
- `outbox_messages`: reliable event publication after commits

### Required identifiers

All externally visible entities should use stable opaque IDs. Every mutating request should support an idempotency key where retries are possible.

## 5. Inventory Ledger and Invariants

The inventory ledger is the authoritative record of quantity movement. Current availability should be derived from ledger state or maintained transactionally with the ledger.

### Initial lifecycle states

```text
AVAILABLE
RESERVED
PICKED_UP
IN_TRANSIT
DELIVERED
SPOILED
DAMAGED
LOST
CANCELLED
```

The implementation must define all permitted transitions and reject invalid transitions.

### Required invariants

For every batch:

```text
original quantity = available + reserved + picked up + in transit
                  + delivered + spoiled + damaged + lost + cancelled
```

Additional requirements:

- No negative quantity
- No quantity can be committed to two active allocations
- A claim expiration cannot release picked-up or in-transit cargo
- Delivered quantities cannot be returned to available stock
- Ledger entries are immutable
- Corrections use compensating entries rather than edits
- Every quantity change references a command, actor, reason, and related event

## 6. State Machines

### Unpicked allocation

```text
AVAILABLE
  -> CLAIMED
  -> ACKNOWLEDGED
  -> PICKED_UP
```

Allowed recovery path:

```text
CLAIMED or ACKNOWLEDGED
  -> EXPIRED
  -> AVAILABLE
```

The expiration worker may release inventory only after verifying that pickup has not been confirmed and no physical custody event exists.

### Physical delivery

```text
PICKED_UP
  -> IN_TRANSIT
  -> DELIVERED
```

Recovery path:

```text
IN_TRANSIT
  -> REROUTE_PENDING
  -> IN_TRANSIT
```

Failure path:

```text
IN_TRANSIT
  -> INCIDENT_REVIEW
```

A reroute must preserve physical custody, remaining quantity, current rider position, safety deadlines, and audit history.

### Shelter lifecycle

```text
OPEN
  -> AT_CAPACITY
  -> CLOSED
  -> REOPENING_REVIEW
  -> OPEN
```

Closing a shelter must trigger revalidation of affected unpicked allocations and in-transit deliveries without silently releasing physical cargo.

## 7. Constraint and Safety Engine

All candidate assignments must pass hard constraints before ranking.

### Hard constraints

1. Inventory quantity is available and exclusive.
2. Rider capacity is not exceeded.
3. Recipient demand and receiving capacity are not exceeded.
4. Pickup, travel, handoff, and safety buffer fit within the safe-handling deadline.
5. Item eligibility and storage requirements are satisfied.
6. Required shelter prerequisites are available or can be fulfilled in time.
7. Receiving hours and staffing requirements are satisfied.
8. Route and destination are currently accessible.
9. Data freshness is within configured limits.
10. The requested operation is authorized for the actor and state.

### Candidate ranking

Only feasible candidates may be ranked. Ranking may consider:

- Expected delivery time
- Spoilage risk
- Recovery time
- Availability of alternative riders and destinations
- Additional travel
- Unmet demand
- Service fairness
- Route uncertainty
- Operational reliability evidence

The ranking result must include the evidence and rule outcomes used to produce it.

### AI boundary

AI may assist with document extraction, summaries, or operator explanations, but it may not:

- Override safety rules
- Mutate inventory directly
- Approve an infeasible assignment
- Create an unverified prerequisite
- Replace deterministic transaction logic

The backend must operate safely when an AI provider is unavailable.

## 8. Last-Safe-Decision Calculation

For every candidate destination, calculate:

```text
latest useful decision time
= safe deadline
- travel duration
- handoff duration
- safety buffer
- destination confirmation time
- rider assignment and notification time
```

The calculation must include uncertainty and data freshness. It should return:

- Remaining safe-handling time
- Estimated travel and handoff duration
- Safety buffer
- Decision deadline
- Confidence or uncertainty value
- Factors that could invalidate the estimate

The deadline monitor should create an incident or escalation before the recovery option becomes infeasible.

## 9. Dispatch and Recovery Workflows

### Dispatch workflow

1. Validate authorization and idempotency key.
2. Load the current version of inventory, rider, shelter, and route data.
3. Generate candidate assignments.
4. Apply hard constraints.
5. Score feasible candidates.
6. Select the best candidate using deterministic tie-breaking.
7. Revalidate all critical inputs inside a database transaction.
8. Create allocation, claim, delivery, ledger, event, and audit records.
9. Publish an outbox event after commit.
10. Return the decision, evidence, and identifiers.

### Ghost reservation recovery

1. Detect expired claim or missed acknowledgement.
2. Verify the allocation was not picked up.
3. Lock and reconcile the affected inventory.
4. Release only eligible quantity.
5. Record the expiration and recovery reason.
6. Recompute feasible assignments.
7. Create a replacement claim or escalate.

### Shelter closure during transit

1. Mark the destination unavailable.
2. Identify affected deliveries.
3. Preserve physical custody and cargo quantity.
4. Generate eligible alternative destinations.
5. Revalidate safety, capacity, prerequisites, and route feasibility.
6. Commit one reroute transactionally, or create an incident.
7. Record the original and new destination plus the decision evidence.

### Safe failure

If no feasible recovery exists:

- Do not fabricate a destination
- Do not release physical cargo to available inventory
- Preserve the last known custody state
- Create an incident with severity and escalation status
- Record all rejected alternatives and reasons

## 10. API Surface

The API should be versioned, documented, and organized around commands and queries.

### Authentication and authorization

```text
POST   /v1/auth/tokens
GET    /v1/me
GET    /v1/roles
```

### Donations and inventory

```text
POST   /v1/batches
GET    /v1/batches/:batchId
GET    /v1/batches/:batchId/ledger
POST   /v1/batches/:batchId/adjustments
GET    /v1/inventory/availability
```

### Riders

```text
POST   /v1/riders
PATCH  /v1/riders/:riderId/status
PATCH  /v1/riders/:riderId/location
POST   /v1/riders/:riderId/heartbeat
GET    /v1/riders/:riderId/tasks
```

### Shelters and demand

```text
POST   /v1/shelters
PATCH  /v1/shelters/:shelterId/demand
PATCH  /v1/shelters/:shelterId/readiness
POST   /v1/shelters/:shelterId/close
POST   /v1/shelters/:shelterId/reopen
GET    /v1/shelters/:shelterId/capacity
```

### Dispatch

```text
POST   /v1/dispatch/preview
POST   /v1/dispatch/commit
GET    /v1/allocations/:allocationId
POST   /v1/allocations/:allocationId/acknowledge
POST   /v1/allocations/:allocationId/pickup
POST   /v1/allocations/:allocationId/deliver
POST   /v1/allocations/:allocationId/cancel
```

### Recovery and incidents

```text
POST   /v1/deliveries/:deliveryId/reroute/preview
POST   /v1/deliveries/:deliveryId/reroute/commit
GET    /v1/incidents
POST   /v1/incidents/:incidentId/resolve
POST   /v1/incidents/:incidentId/escalate
```

### Simulation

```text
POST   /v1/scenarios
POST   /v1/scenarios/:scenarioId/start
POST   /v1/scenarios/:scenarioId/advance-time
POST   /v1/scenarios/:scenarioId/inject-failure
GET    /v1/scenarios/:scenarioId/state
GET    /v1/scenarios/:scenarioId/replay
POST   /v1/scenarios/:scenarioId/compare-baseline
```

### Audit and operations

```text
GET    /v1/events
GET    /v1/audit/decisions/:decisionId
GET    /v1/audit/inventory/:batchId
GET    /v1/health
GET    /v1/ready
GET    /v1/metrics
```

All mutating endpoints should support:

- Request validation
- Authorization checks
- Idempotency keys
- Correlation IDs
- Optimistic version checks where applicable
- Structured error responses
- Audit evidence

## 11. Error Model

Use stable machine-readable error codes with human-readable explanations.

Example categories:

```text
INVENTORY_INSUFFICIENT
INVENTORY_CONFLICT
RIDER_CAPACITY_EXCEEDED
RECIPIENT_CAPACITY_EXCEEDED
SAFETY_DEADLINE_UNSAFE
MISSING_PREREQUISITE
DESTINATION_UNAVAILABLE
ROUTE_INFEASIBLE
CLAIM_EXPIRED
INVALID_STATE_TRANSITION
STALE_VERSION
AUTHORIZATION_DENIED
RECOVERY_NOT_FEASIBLE
```

Errors must identify whether the request can be retried, requires new input, or requires operator escalation.

## 12. Background Workers

### Reservation expiration worker

- Finds expired claims
- Uses a transaction to verify claim and custody state
- Releases only eligible unpicked inventory
- Emits an expiration event
- Starts replacement dispatch or escalation

### Heartbeat and acknowledgement worker

- Tracks rider acknowledgement deadlines
- Distinguishes connectivity loss from confirmed refusal where possible
- Avoids penalizing a rider solely from one missed heartbeat
- Escalates when evidence crosses configured thresholds

### Safety-deadline worker

- Recalculates remaining feasibility
- Flags candidates approaching their latest useful decision time
- Creates incidents before deadlines are missed

### Recovery worker

- Processes shelter closures, route failures, rider failures, and demand changes
- Revalidates all affected assignments
- Commits recoveries transactionally
- Prevents duplicate recovery attempts using idempotency and locking

### Outbox publisher

- Publishes committed operational events
- Retries safely
- Records delivery attempts
- Never publishes an event for a transaction that rolled back

## 13. Event and Audit Model

Every important command should produce a domain event and an audit record.

Audit records should include:

- Event ID
- Actor or system worker
- Timestamp from the authoritative clock
- Correlation ID
- Command and input summary
- Relevant entity versions
- Constraints evaluated
- Candidate alternatives
- Decision and outcome
- Rejection or escalation reasons
- Source data freshness
- Whether the result came from live or simulated time

The audit log should be append-only. Corrections should be represented by new events.

## 14. Simulation Backend

The simulation engine must reuse the live domain services and rules.

### Required capabilities

- Deterministic seed
- Accelerated clock
- Event injection
- Rider failure
- Shelter closure
- Demand changes
- Expiry deadlines
- Route and flood disruption
- Missing prerequisites
- Cascading failures
- Concurrent claim attempts
- State snapshots
- Replay from a snapshot
- Baseline comparison

### Simulation isolation

Simulation data must be isolated from live operational data. A scenario should have its own tenant or database namespace and must never mutate production records.

## 15. Testing Strategy

### Unit tests

- Quantity calculations
- State transitions
- Safety deadline calculations
- Prerequisite evaluation
- Candidate ranking and deterministic tie-breaking
- Last-safe-decision calculations
- Error classification

### Integration tests

- Database transactions
- Ledger reconciliation
- API authorization
- Outbox delivery
- Worker retries
- Idempotent commands

### Concurrency tests

- Overlapping claims
- Simultaneous shelter closure and dispatch
- Duplicate pickup confirmation
- Concurrent expiration and pickup
- Concurrent reroute attempts
- Recovery competing for limited destinations

### Property and invariant tests

- Inventory can never become negative
- Quantity conservation always holds
- No conflicting active allocation exists
- Unsafe assignments are never committed
- Picked-up inventory is never returned to available stock
- Replaying the same deterministic scenario produces the same result

### Scenario tests

1. Oversized donation split
2. Ghost reservation
3. Shelter closure during transit
4. Expiry infeasibility
5. Missing prerequisites
6. Cascading rider and shelter failure
7. Flood disruption
8. Concurrency stress

## 16. Evaluation and Baseline

The baseline should use nearest-feasible-recipient matching with the same input data, safety rules, route estimates, and tie-breaking policy, but without resilience-aware scoring or contingency planning.

Compare both systems using fixed seeds and repeatable workloads.

Metrics:

- Safe delivery completion rate
- Spoiled quantity
- Unmet demand
- Recovery success rate
- Recovery time
- Additional recovery travel
- Unsafe assignment count
- Duplicate allocation violations
- Dispatch decision latency
- Fairness of service coverage
- Number of escalated incidents

Safety violations and quantity-conservation failures are hard failures, not average metrics.

## 17. Security, Privacy, and Reliability

The backend must include:

- Role-based authorization enforced server-side
- Least-privilege service credentials
- PII minimization
- Protected rider location data
- Audit-log access controls
- Request rate limiting
- Input and file validation
- Secret management outside source control
- Idempotent retry handling
- Database backups and restore testing
- Structured logs without sensitive payloads
- Health and readiness checks
- Monitoring for failed jobs and stale data
- Explicit emergency-override authorization and audit records

## 18. Backend Implementation Phases

### Phase 1 — Domain foundation

- Define Python domain models and typed schemas
- Define state machines and transitions
- Define Supabase database schema and migrations
- Implement authoritative clock abstraction
- Add reproducible seed data
- Add error and event conventions

Exit criteria: domain state can be created, read, and validated without a frontend.

### Phase 2 — Inventory ledger

- Implement immutable ledger entries
- Add quantity reconciliation
- Add batch and allocation records
- Add transaction boundaries
- Add idempotency support

Exit criteria: inventory cannot be negative or double-allocated under tested concurrent operations.

### Phase 3 — Constraint and safety engine

- Implement candidate generation
- Implement hard constraints
- Implement compatibility and prerequisite checks
- Implement deadline calculations
- Implement explainable decisions

Exit criteria: unsafe or infeasible assignments are rejected with stable reasons.

### Phase 4 — Dispatch API

- Implement preview and commit commands
- Add claims and acknowledgement deadlines
- Add pickup and delivery transitions
- Add authorization and audit events
- Add outbox publishing

Exit criteria: a complete safe dispatch can be executed through APIs and reconstructed from events.

### Phase 5 — Recovery engine

- Add expiration and heartbeat workers
- Add shelter closure recovery
- Add in-transit reroute workflow
- Add alternative destination scoring
- Add incident escalation

Exit criteria: ghost reservations and shelter closures recover safely or produce explicit incidents.

### Phase 6 — Simulation and baseline

- Add isolated scenario state
- Add accelerated time
- Add failure injection
- Add deterministic replay
- Add baseline implementation
- Generate evaluation reports

Exit criteria: all judge scenarios run reproducibly through backend APIs or scenario commands.

### Phase 7 — Hardening

- Run concurrency and property tests
- Add monitoring and operational metrics
- Document deployment and recovery procedures
- Verify clean-environment setup
- Perform security and failure-mode review

Exit criteria: backend can be deployed independently and its critical invariants are verified.

## 19. Backend Definition of Done

The backend is ready for the first judge demonstration when:

- Inventory quantity is conserved across all tested transitions.
- Concurrent claims cannot double-allocate inventory.
- Capacity, demand, compatibility, and safety constraints are enforced server-side.
- Expired unpicked claims are recovered safely.
- Picked-up and in-transit cargo is never released as available inventory.
- Shelter closure triggers controlled recovery.
- No feasible recovery creates an explicit incident.
- Every dispatch and recovery decision has inspectable evidence.
- Simulation scenarios are deterministic and isolated from live data.
- Baseline comparisons use reproducible inputs.
- APIs, workers, migrations, tests, and local setup are documented.
- A future frontend can use the backend without implementing business rules itself.
