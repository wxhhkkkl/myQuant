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
                    params        TEXT NOT NULL,
                    stock_list    TEXT,
                    is_active     BOOLEAN DEFAULT 0,
                    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (model_name) REFERENCES quant_models(model_name)
                )
            """)

    @staticmethod
    def upsert(model_name: str, params: dict, config_name: str = None,
               stock_list: list = None):
        with get_db() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO strategy_configs
                    (model_name, config_name, params, stock_list, is_active)
                VALUES (?, ?, ?, ?, 1)
            """, (model_name, config_name, json.dumps(params, ensure_ascii=False),
                  json.dumps(stock_list, ensure_ascii=False) if stock_list else None))

    @staticmethod
    def get(model_name: str) -> dict:
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM strategy_configs WHERE model_name = ? AND is_active = 1",
                (model_name,)
            ).fetchone()
        return dict(row) if row else None
