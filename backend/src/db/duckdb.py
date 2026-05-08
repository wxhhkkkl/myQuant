import duckdb
from contextlib import contextmanager
from backend.src.config import DUCKDB_PATH


class DuckDBManager:
    """DuckDB connection manager with read-only pool for concurrent reads."""

    def __init__(self, path: str = DUCKDB_PATH):
        self.path = path
        self._write_conn = None
        self._read_conn = None

    @property
    def write_conn(self):
        if self._write_conn is None:
            self._write_conn = duckdb.connect(str(self.path))
        return self._write_conn

    @property
    def read_conn(self):
        if self._read_conn is None:
            self._read_conn = duckdb.connect(str(self.path))
        return self._read_conn

    def execute(self, sql: str, params=None):
        return self.write_conn.execute(sql, params)

    def query(self, sql: str, params=None):
        return self.read_conn.execute(sql, params)

    def query_df(self, sql: str, params=None):
        return self.read_conn.execute(sql, params).df()

    def close(self):
        if self._write_conn:
            self._write_conn.close()
        if self._read_conn:
            self._read_conn.close()


db = DuckDBManager()
