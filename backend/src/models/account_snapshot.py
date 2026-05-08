from backend.src.db.sqlite import get_db


class AccountSnapshot:
    @staticmethod
    def create_table():
        with get_db() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS account_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    total_asset REAL NOT NULL,
                    available_cash REAL NOT NULL DEFAULT 0,
                    market_value REAL NOT NULL DEFAULT 0,
                    snapshot_date DATE NOT NULL DEFAULT (date('now')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    @staticmethod
    def create(total_asset: float, available_cash: float = 0.0,
               market_value: float = 0.0, snapshot_date: str = None) -> int:
        with get_db() as conn:
            cur = conn.execute(
                "INSERT INTO account_snapshots (total_asset, available_cash, market_value, snapshot_date) "
                "VALUES (?, ?, ?, ?)",
                (total_asset, available_cash, market_value,
                 snapshot_date or __import__('datetime').date.today().isoformat())
            )
            return cur.lastrowid

    @staticmethod
    def recent(limit: int = 30) -> list:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM account_snapshots ORDER BY snapshot_date DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [dict(r) for r in rows]
