-- Vigilo Phase 4 Database Migration: Transactional Outbox & Audit Records
-- Tables: outbox_messages, audit_records

create table if not exists public.audit_records (
  id text primary key,
  event_id text,
  actor text not null,
  command text not null,
  decision text not null,
  constraints_evaluated text[] not null default '{}',
  evidence jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists audit_records_event_idx on public.audit_records(event_id);
create index if not exists audit_records_actor_idx on public.audit_records(actor);
create index if not exists audit_records_created_idx on public.audit_records(created_at);

create table if not exists public.outbox_messages (
  id text primary key,
  event_id text not null,
  event_type text not null,
  topic text not null default 'dispatch',
  payload jsonb not null default '{}'::jsonb,
  status text not null default 'PENDING' check (status in ('PENDING', 'PUBLISHED', 'FAILED')),
  retry_count integer not null default 0 check (retry_count >= 0),
  last_error text,
  created_at timestamptz not null default now(),
  published_at timestamptz
);

create index if not exists outbox_status_idx on public.outbox_messages(status, created_at);
create index if not exists outbox_event_id_idx on public.outbox_messages(event_id);
