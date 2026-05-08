from backend.src.db.sqlite import get_db


class StockFundamental:
    @staticmethod
    def create_table():
        with get_db() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stock_fundamentals (
                    stock_code     VARCHAR(10) NOT NULL,
                    snap_date      DATE NOT NULL,
                    market_cap     DOUBLE,
                    pe_ratio       DOUBLE,
                    pb_ratio       DOUBLE,
                    eps            DOUBLE,
                    high_52w       DOUBLE,
                    low_52w        DOUBLE,
                    updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (stock_code, snap_date),
                    FOREIGN KEY (stock_code) REFERENCES stocks(stock_code)
                )
            """)

    @staticmethod
    def upsert(code: str, snap_date: str, market_cap: float = None,
               pe_ratio: float = None, pb_ratio: float = None,
               eps: float = None, high_52w: float = None, low_52w: float = None):
        with get_db() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO stock_fundamentals
                    (stock_code, snap_date, market_cap, pe_ratio, pb_ratio,
                     eps, high_52w, low_52w)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (code, snap_date, market_cap, pe_ratio, pb_ratio,
                  eps, high_52w, low_52w))

    @staticmethod
    def latest(code: str) -> dict:
        with get_db() as conn:
            row = conn.execute("""
                SELECT * FROM stock_fundamentals
                WHERE stock_code = ?
                ORDER BY snap_date DESC LIMIT 1
            """, (code,)).fetchone()
        return dict(row) if row else None
