import json
from backend.src.db.sqlite import get_db


class StrategyConfig:
    @staticmethod
    def create_table():
        with get_db() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS strategy_configs (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_name    VARCHAR(50) NOT NULL,
                    config_name   VARCHAR(100),
                    stock_code    VARCHAR(10),
                    params        TEXT NOT NULL,
                    position_pct  INTEGER DEFAULT 100,
                    time_range    VARCHAR(5) DEFAULT '1y',
                    stock_list    TEXT,
                    is_active     BOOLEAN DEFAULT 0,
                    is_running    INTEGER DEFAULT 0,
                    capital       REAL DEFAULT 100000,
                    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (model_name) REFERENCES quant_models(model_name)
                )
            """)
            # Add columns if upgrading from older schema
            for col, col_type in [("stock_code", "VARCHAR(10)"), ("position_pct", "INTEGER DEFAULT 100"),
                                   ("time_range", "VARCHAR(5) DEFAULT '1y'"),
                                   ("is_running", "INTEGER DEFAULT 0"),
                                   ("capital", "REAL DEFAULT 100000")]:
                try:
                    conn.execute(f"ALTER TABLE strategy_configs ADD COLUMN {col} {col_type}")
                except Exception:
                    pass

    @staticmethod
    def upsert(model_name: str, params: dict, config_name: str = None,
               stock_code: str = None, position_pct: int = 100, time_range: str = "1y",
               stock_list: list = None):
        with get_db() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO strategy_configs
                    (model_name, config_name, stock_code, params, position_pct, time_range, stock_list, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """, (model_name, config_name, stock_code, json.dumps(params, ensure_ascii=False),
                  position_pct, time_range,
                  json.dumps(stock_list, ensure_ascii=False) if stock_list else None))

    @staticmethod
    def get(model_name: str) -> dict:
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM strategy_configs WHERE model_name = ? AND is_active = 1",
                (model_name,)
            ).fetchone()
        return dict(row) if row else None

    @staticmethod
    def set_running(model_name: str, is_running: bool):
        with get_db() as conn:
            conn.execute(
                "UPDATE strategy_configs SET is_running = ? WHERE model_name = ? AND is_active = 1",
                (1 if is_running else 0, model_name)
            )

    @staticmethod
    def get_running_models() -> list:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM strategy_configs WHERE is_running = 1 AND is_active = 1"
            ).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def set_capital(model_name: str, capital: float):
        with get_db() as conn:
            conn.execute(
                "UPDATE strategy_configs SET capital = ? WHERE model_name = ? AND is_active = 1",
                (capital, model_name)
            )
