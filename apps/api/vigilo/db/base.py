"""Database base configurations and cross-dialect type decorators."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, String, TypeDecorator
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class TextArray(TypeDecorator):
    """Stores list/set of strings. Uses Postgres native ARRAY or JSON for SQLite."""

    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_ARRAY(String))
        return dialect.type_descriptor(String)

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None if dialect.name == "postgresql" else "[]"
        if dialect.name == "postgresql":
            return list(value)
        return json.dumps(sorted(list(value)))

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return []
        if dialect.name == "postgresql":
            return list(value)
        if isinstance(value, str):
            try:
                return json.loads(value)
            except Exception:
                return []
        return list(value)


class JsonObject(TypeDecorator):
    """Stores dictionary payloads. Uses Postgres JSONB or String JSON for SQLite."""

    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_JSONB)
        return dialect.type_descriptor(String)

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None if dialect.name == "postgresql" else "{}"
        if dialect.name == "postgresql":
            return value
        return json.dumps(value)

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return {}
        if dialect.name == "postgresql":
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except Exception:
                return {}
        return value


class UTCDateTime(TypeDecorator):
    """Ensures datetimes are timezone-aware UTC."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is not None:
            if isinstance(value, datetime):
                if value.tzinfo is None:
                    value = value.replace(tzinfo=timezone.utc)
                else:
                    value = value.astimezone(timezone.utc)
        return value

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        if value is not None and isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            else:
                value = value.astimezone(timezone.utc)
        return value
