import json
from backend.src.db.sqlite import get_db


class QuantModel:
    @staticmethod
    def create_table():
        with get_db() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS quant_models (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_name VARCHAR(50) NOT NULL UNIQUE,
                    display_name VARCHAR(100),
                    description TEXT,
                    default_params TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    @staticmethod
    def register(model_name: str, display_name: str, description: str,
                 default_params: dict):
        with get_db() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO quant_models
                    (model_name, display_name, description, default_params, is_active)
                VALUES (?, ?, ?, ?, 1)
            """, (model_name, display_name, description,
                  json.dumps(default_params, ensure_ascii=False)))

    @staticmethod
    def all_active() -> list:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM quant_models WHERE is_active = 1"
            ).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def get(model_name: str) -> dict:
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM quant_models WHERE model_name = ?", (model_name,)
            ).fetchone()
        return dict(row) if row else None
