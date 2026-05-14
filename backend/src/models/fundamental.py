from backend.src.db.sqlite import get_db


class StockFundamental:
    @staticmethod
    def create_table():
        with get_db() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stock_fundamentals (
                    stock_code          VARCHAR(10) NOT NULL,
                    snap_date           DATE NOT NULL,
                    market_cap          DOUBLE,
                    pe_ratio            DOUBLE,
                    pb_ratio            DOUBLE,
                    eps                 DOUBLE,
                    high_52w            DOUBLE,
                    low_52w             DOUBLE,
                    dividend_yield      DOUBLE,
                    book_value_per_share DOUBLE,
                    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (stock_code, snap_date),
                    FOREIGN KEY (stock_code) REFERENCES stocks(stock_code)
                )
            """)
            # Ensure new columns exist for older DBs
            for col, dtype in [("dividend_yield", "DOUBLE"), ("book_value_per_share", "DOUBLE")]:
                try:
                    conn.execute(f"ALTER TABLE stock_fundamentals ADD COLUMN {col} {dtype}")
                except Exception:
                    pass

    @staticmethod
    def upsert(code: str, snap_date: str, market_cap: float = None,
               pe_ratio: float = None, pb_ratio: float = None,
               eps: float = None, high_52w: float = None, low_52w: float = None,
               dividend_yield: float = None, book_value_per_share: float = None):
        with get_db() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO stock_fundamentals
                    (stock_code, snap_date, market_cap, pe_ratio, pb_ratio,
                     eps, high_52w, low_52w, dividend_yield, book_value_per_share)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (code, snap_date, market_cap, pe_ratio, pb_ratio,
                  eps, high_52w, low_52w, dividend_yield, book_value_per_share))

    @staticmethod
    def latest(code: str) -> dict:
        with get_db() as conn:
            row = conn.execute("""
                SELECT * FROM stock_fundamentals
                WHERE stock_code = ?
                ORDER BY snap_date DESC LIMIT 1
            """, (code,)).fetchone()
        return dict(row) if row else None
