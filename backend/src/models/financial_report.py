from backend.src.db.sqlite import get_db


class FinancialReport:
    @staticmethod
    def create_table():
        with get_db() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS financial_reports (
                    stock_code        VARCHAR(10) NOT NULL,
                    report_period     VARCHAR(7) NOT NULL,
                    revenue           DOUBLE,
                    net_profit        DOUBLE,
                    roe               DOUBLE,
                    debt_ratio        DOUBLE,
                    eps               DOUBLE,
                    report_type       VARCHAR(10),
                    updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (stock_code, report_period),
                    FOREIGN KEY (stock_code) REFERENCES stocks(stock_code)
                )
            """)

    @staticmethod
    def upsert(code: str, period: str, revenue: float = None,
               net_profit: float = None, roe: float = None,
               debt_ratio: float = None, eps: float = None,
               report_type: str = None):
        with get_db() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO financial_reports
                    (stock_code, report_period, revenue, net_profit,
                     roe, debt_ratio, eps, report_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (code, period, revenue, net_profit, roe, debt_ratio, eps,
                  report_type))

    @staticmethod
    def for_stock(code: str) -> list:
        with get_db() as conn:
            rows = conn.execute("""
                SELECT * FROM financial_reports
                WHERE stock_code = ?
                ORDER BY report_period DESC
                LIMIT 8
            """, (code,)).fetchall()
        return [dict(r) for r in rows]
