"""PostgreSQL persistent backend adapter for Vigilo."""
from __future__ import annotations

from .persistent_service import PersistentDispatchService


class PostgresDispatchService(PersistentDispatchService):
    """PostgreSQL-backed dispatch service with full transaction and ledger persistence."""

    def __init__(self, database_url: str | None = None, clock=None) -> None:
        if database_url:
            from ..db.session import configure_db
            configure_db(database_url)
        super().__init__(clock=clock)
