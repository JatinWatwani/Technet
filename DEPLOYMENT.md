# Vigilo Backend — Deployment & Operations Runbook

This runbook describes the production deployment, database migration, monitoring setup, and disaster recovery procedures for the **Vigilo** resilience-aware logistics engine.

---

## 1. System Architecture & Topology

Vigilo is designed to operate statelessly with clean horizontal scaling:
- **Application Server**: FastAPI running under ASGI (`uvicorn` / `gunicorn` with `uvicorn.workers.UvicornWorker`).
- **Database Layer**: PostgreSQL 15+ (or Supabase Managed Postgres) with row-level locking (`SELECT ... FOR UPDATE`), transaction isolation, and immutable double-entry ledger tables.
- **Worker Processes**: Autonomous sweep worker execution via cron/scheduled endpoints (`POST /v1/workers/run-sweeps`) or background asynchronous workers.
- **Observability**: Prometheus-compatible metric scrapers (`GET /v1/metrics`) and Kubernetes liveness/readiness probes (`GET /v1/health`, `GET /v1/ready`).

---

## 2. Environment Variables & Secret Configuration

Never commit sensitive credentials to source control. Set the following environment variables:

| Variable | Description | Example / Default |
|---|---|---|
| `VIGILO_ENV` | Environment identifier | `production`, `staging`, `development` |
| `CLOCK_MODE` | Authoritative time provider | `SYSTEM` (for live operations), `SIMULATED` (for tests/scenarios) |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host:5432/vigilo` |
| `SUPABASE_URL` | Supabase API URL (if using Supabase) | `https://xxxx.supabase.co` |
| `SUPABASE_SECRET_KEY` | Service-role key with bypass RLS | `ey...` |
| `LOG_LEVEL` | Application logging verbosity | `INFO`, `DEBUG`, `WARNING` |
| `PROMETHEUS_METRICS` | Enable Prometheus endpoint | `true` |

---

## 3. Database Migrations & Seeding

Migrations are located in `database/migrations/`:
- `001_initial.sql`: Core schema, domain entities, and baseline constraints.
- `002_foundation.sql`: Double-entry inventory ledger, allocations, deliveries, incidents, audit records, and transactional PostgreSQL functions (`dispatch_allocation`, `pickup_delivery`, etc.).

### Applying Migrations
Via `psql`:
```bash
psql "$DATABASE_URL" -f database/migrations/001_initial.sql
psql "$DATABASE_URL" -f database/migrations/002_foundation.sql
```

Via Supabase:
Execute the contents of `001_initial.sql` and `002_foundation.sql` sequentially in the Supabase SQL Editor.

### Verifying Schema Integrity
Verify that the `inventory_ledger_entries` table has unique constraints on `idempotency_key` and foreign key relationships across batches and allocations.

---

## 4. Production Deployment

### Docker Deployment
```dockerfile
FROM python:3.13-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY apps/ ./apps/

RUN pip install --no-cache-dir .

EXPOSE 8000
CMD ["uvicorn", "vigilo.main:app", "--app-dir", "apps/api", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### Kubernetes Pod Probes
Configure Kubernetes liveness and readiness probes:
```yaml
livenessProbe:
  httpGet:
    path: /v1/health
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /v1/ready
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 15
```

---

## 5. Background Sweep Worker Setup

Autonomous workers must run periodically to sweep expired leases and monitor rider telemetry:
- **Frequency**: Every 60 to 120 seconds.
- **Trigger**: An internal scheduler or external HTTP ping:
```bash
curl -X POST https://api.vigilo.org/v1/workers/run-sweeps \
     -H "X-Actor: worker_cron" \
     -H "X-Actor-Role: SYSTEM"
```
The endpoint returns:
- `expired_allocations_count`: Number of unacknowledged claims expired and restored to available inventory.
- `stale_rider_heartbeats_count`: Number of riders switched offline due to lost heartbeat.
- `safety_deadline_incidents_count`: Proactive incidents raised before perishables spoil.

---

## 6. Disaster Recovery & Emergency Procedures

### Emergency Overrides
In catastrophic disaster scenarios (e.g. hurricane landfall, military conflict), an authorized coordinator (`ADMIN` role) can relax normal constraint restrictions:
```bash
curl -X POST https://api.vigilo.org/v1/emergency/override \
     -H "Content-Type: application/json" \
     -H "X-Actor-Role: ADMIN" \
     -H "X-Actor: Director Maria Santos" \
     -d '{
       "override_type": "RECEIVING_HOURS_OVERRIDE",
       "target_entity_type": "Shelter",
       "target_entity_id": "shelter_eastside",
       "justification": "Hurricane disaster declaration: open shelter 24/7 for relief delivery",
       "authorized_by": "Director Maria Santos"
     }'
```
All emergency overrides are permanently recorded in the immutable audit log and domain event stream.

### Inventory Discrepancy Reconciliation
If an unexpected physical discrepancy occurs (e.g., box damaged during transit):
```bash
curl -X POST https://api.vigilo.org/v1/batches/{batch_id}/adjust \
     -H "Content-Type: application/json" \
     -H "X-Actor-Role: ADMIN" \
     -d '{
       "quantity": 5,
       "from_state": "PICKED_UP",
       "to_state": "DAMAGED",
       "reason": "Water container punctured during transit"
     }'
```
This inserts a compensating adjustment ledger record while preserving mathematical reconciliation.
