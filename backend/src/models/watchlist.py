from backend.src.db.sqlite import get_db


class Watchlist:
    @staticmethod
    def create_table():
        with get_db() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS watchlist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stock_code VARCHAR(10) NOT NULL UNIQUE,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT,
                    FOREIGN KEY (stock_code) REFERENCES stocks(stock_code)
                )
            """)

    @staticmethod
    def add(code: str, notes: str = None):
        with get_db() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO watchlist (stock_code, notes) VALUES (?, ?)",
                (code, notes)
            )

    @staticmethod
    def remove(code: str):
        with get_db() as conn:
            conn.execute(
                "DELETE FROM watchlist WHERE stock_code = ?", (code,)
            )

    @staticmethod
    def all() -> list:
        with get_db() as conn:
            rows = conn.execute("""
                SELECT w.*, s.stock_name FROM watchlist w
                JOIN stocks s ON w.stock_code = s.stock_code
                ORDER BY w.added_at DESC
            """).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def contains(code: str) -> bool:
        with get_db() as conn:
            row = conn.execute(
                "SELECT 1 FROM watchlist WHERE stock_code = ?", (code,)
            ).fetchone()
        return row is not None
