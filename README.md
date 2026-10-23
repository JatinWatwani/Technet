# Vigilo Backend

Initial backend foundation for the Vigilo resilience-aware humanitarian logistics engine.

## Current slice

This first implementation provides:

- Python domain models for batches, riders, shelters, and allocations
- A deterministic in-memory dispatch service
- Inventory, rider-capacity, shelter-demand, prerequisite, and safety-deadline checks
- Preview and commit API endpoints
- Tests for accepted and rejected dispatch decisions

The repository now supports the supplied Supabase project as its persistence layer. Without a Supabase secret key, the API falls back to an in-memory demo service for local tests only.

## Supabase setup

1. Copy `.env.example` to `.env` or export the variables in the server environment.
2. Set `DATABASE_URL` to the server-only PostgreSQL connection URL. URL-encode reserved password characters such as `@` as `%40`. Never commit this URL.
3. Run `database/migrations/001_initial.sql` in the Supabase SQL editor.
4. Seed rows in the `batches`, `riders`, and `shelters` tables before calling dispatch endpoints.

When `DATABASE_URL` is set, the API reads current rows from Supabase PostgreSQL and commits dispatches through the transactional `dispatch_allocation` PostgreSQL function. If `DATABASE_URL` is absent, `SUPABASE_SECRET_KEY` can be used with the Supabase client adapter instead.

## Install

```bash
python -m pip install -e ".[dev]"
```

## Run checks

```bash
python -m pytest
```

## Run the API

```bash
uvicorn oopsloop.main:app --app-dir apps/api --reload
```

Health check: `GET /health`
