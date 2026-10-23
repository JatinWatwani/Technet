-- Vigilo Phase 2 Database Migration: Immutable Inventory Ledger & Concurrency
-- Tables: inventory_ledger_entries, idempotency_keys, triggers for append-only immutability

-- 1. Idempotency Keys table for safe network retries
create table if not exists public.idempotency_keys (
  key text primary key,
  scope text not null default 'global',
  status text not null check (status in ('IN_PROGRESS', 'COMPLETED', 'FAILED')),
  response_payload jsonb,
  created_at timestamptz not null default now(),
  expires_at timestamptz not null default (now() + interval '24 hours')
);

create index if not exists idempotency_expires_idx on public.idempotency_keys(expires_at);

-- 2. Inventory Ledger Entries table (Strictly append-only)
create table if not exists public.inventory_ledger_entries (
  id text primary key,
  batch_id text not null references public.batches(id) on delete restrict,
  entry_type text not null check (
    entry_type in (
      'INTAKE', 'RESERVATION_HOLD', 'RESERVATION_RELEASE', 'PICKUP_CONFIRMED',
      'DELIVERY_CONFIRMED', 'SPOILAGE_RECORDED', 'DAMAGE_RECORDED',
      'LOSS_RECORDED', 'COMPENSATING_ADJUSTMENT'
    )
  ),
  quantity integer not null check (quantity > 0),
  from_state text check (
    from_state in (
      'AVAILABLE', 'RESERVED', 'PICKED_UP', 'IN_TRANSIT', 'DELIVERED',
      'SPOILED', 'DAMAGED', 'LOST', 'CANCELLED'
    )
  ),
  to_state text not null check (
    to_state in (
      'AVAILABLE', 'RESERVED', 'PICKED_UP', 'IN_TRANSIT', 'DELIVERED',
      'SPOILED', 'DAMAGED', 'LOST', 'CANCELLED'
    )
  ),
  actor text not null,
  command text not null,
  reason text not null,
  occurred_at timestamptz not null default now(),
  balance_available integer not null check (balance_available >= 0),
  balance_reserved integer not null check (balance_reserved >= 0),
  balance_picked_up integer not null check (balance_picked_up >= 0),
  balance_delivered integer not null check (balance_delivered >= 0),
  balance_spoiled integer not null default 0 check (balance_spoiled >= 0),
  balance_damaged integer not null default 0 check (balance_damaged >= 0),
  balance_lost integer not null default 0 check (balance_lost >= 0),
  allocation_id uuid references public.allocations(id) on delete set null,
  delivery_id text references public.deliveries(id) on delete set null,
  idempotency_key text,
  correlation_id text not null,
  metadata jsonb not null default '{}'::jsonb
);

create index if not exists ledger_batch_idx on public.inventory_ledger_entries(batch_id, occurred_at);
create unique index if not exists ledger_idempotency_idx on public.inventory_ledger_entries(idempotency_key) where idempotency_key is not null;

-- 3. Trigger preventing updates or deletes on inventory_ledger_entries
create or replace function public.enforce_ledger_immutability()
returns trigger
language plpgsql
as $$
begin
  raise exception 'Inventory ledger entries are strictly immutable and cannot be updated or deleted. Use compensating adjustments instead.'
    using detail = 'LEDGER_IMMUTABLE';
end;
$$;

drop trigger if exists trg_prevent_ledger_mutation on public.inventory_ledger_entries;
create trigger trg_prevent_ledger_mutation
before update or delete on public.inventory_ledger_entries
for each row
execute function public.enforce_ledger_immutability();
