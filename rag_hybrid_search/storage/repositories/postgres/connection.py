"""Shared, pooled Postgres connection -- every Postgres repository in this
package takes a ``ConnectionProvider`` (this pool, or the fixed single
connection a unit-of-work hands out mid-transaction) rather than opening its
own ``psycopg.connect()``. One process, one pool.
"""

from contextlib import contextmanager
from typing import Iterator, Protocol

import psycopg
from psycopg_pool import ConnectionPool


class ConnectionProvider(Protocol):
    def connection(self) -> Iterator[psycopg.Connection]:
        """Context manager yielding a connection. Implementations decide
        the transaction boundary: a pool commits/releases per call (fine
        for standalone reads); a unit-of-work holds one connection open
        across several repository calls and commits once, at the end."""
        ...


class PostgresConnectionPool:
    """Thin wrapper around psycopg_pool.ConnectionPool -- constructed once
    in the composition root (api/dependencies.py) and shared by every
    repository and unit-of-work in the process."""

    def __init__(self, dsn: str, min_size: int = 1, max_size: int = 10, statement_timeout_ms: int = 30_000):
        # statement_timeout: a hung/runaway query used to be able to hold a
        # pool connection indefinitely, starving every other repository call
        # (and, once multiple workers share this pool, every other job) --
        # no timeout existed anywhere on the Postgres path before this.
        self._pool = ConnectionPool(
            dsn, min_size=min_size, max_size=max_size, open=True,
            kwargs={"options": f"-c statement_timeout={statement_timeout_ms}"},
        )

    @contextmanager
    def connection(self) -> Iterator[psycopg.Connection]:
        with self._pool.connection() as conn:
            yield conn

    def raw_connection_context(self):
        """Returns the pool's connection() context manager, unentered --
        for a unit-of-work that needs to hold one connection open across
        multiple repository calls instead of one per call (see
        PostgresIngestionUnitOfWork)."""
        return self._pool.connection()

    def close(self) -> None:
        self._pool.close()
