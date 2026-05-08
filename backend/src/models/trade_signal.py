from backend.src.db.sqlite import get_db


class TradeSignal:
    @staticmethod
    def create_table():
        with get_db() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trade_signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stock_code VARCHAR(10) NOT NULL,
                    model_name VARCHAR(50) NOT NULL,
                    signal_type VARCHAR(10) NOT NULL,
                    signal_price REAL NOT NULL,
                    signal_reason TEXT,
                    is_confirmed INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    @staticmethod
    def create(stock_code: str, model_name: str, signal_type: str,
               signal_price: float, signal_reason: str = None) -> int:
        with get_db() as conn:
            cur = conn.execute(
                "INSERT INTO trade_signals (stock_code, model_name, signal_type, signal_price, signal_reason) "
                "VALUES (?, ?, ?, ?, ?)",
                (stock_code, model_name, signal_type, signal_price, signal_reason)
            )
            return cur.lastrowid

    @staticmethod
    def get(signal_id: int) -> dict | None:
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM trade_signals WHERE id = ?", (signal_id,)
            ).fetchone()
        return dict(row) if row else None

    @staticmethod
    def confirm(signal_id: int):
        with get_db() as conn:
            conn.execute(
                "UPDATE trade_signals SET is_confirmed = 1 WHERE id = ?",
                (signal_id,)
            )

    @staticmethod
    def dismiss(signal_id: int):
        with get_db() as conn:
            conn.execute("DELETE FROM trade_signals WHERE id = ?", (signal_id,))

    @staticmethod
    def pending() -> list:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM trade_signals WHERE is_confirmed = 0 ORDER BY created_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def all() -> list:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM trade_signals ORDER BY created_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]
