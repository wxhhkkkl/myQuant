from dataclasses import dataclass
from typing import Optional
from backend.src.db.sqlite import get_db


@dataclass
class Stock:
    stock_code: str
    stock_name: str
    industry: Optional[str] = None
    sub_industry: Optional[str] = None
    exchange: Optional[str] = None
    list_date: Optional[str] = None
    is_active: bool = True

    @staticmethod
    def create_table():
        with get_db() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stocks (
                    stock_code VARCHAR(10) PRIMARY KEY,
                    stock_name VARCHAR(50) NOT NULL,
                    industry VARCHAR(50),
                    sub_industry VARCHAR(50),
                    exchange VARCHAR(10),
                    list_date DATE,
                    is_active BOOLEAN DEFAULT 1
                )
            """)

    @staticmethod
    def upsert(code: str, name: str, industry: str = None,
               sub_industry: str = None, exchange: str = None,
               list_date: str = None):
        with get_db() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO stocks (stock_code, stock_name, industry,
                    sub_industry, exchange, list_date, is_active)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            """, (code, name, industry, sub_industry, exchange, list_date))

    @staticmethod
    def search(keyword: str) -> list:
        with get_db() as conn:
            rows = conn.execute("""
                SELECT * FROM stocks
                WHERE stock_code LIKE ? OR stock_name LIKE ?
                LIMIT 20
            """, (f"%{keyword}%", f"%{keyword}%")).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def get(code: str) -> Optional[dict]:
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM stocks WHERE stock_code = ?", (code,)
            ).fetchone()
        return dict(row) if row else None

    @staticmethod
    def all_active() -> list:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM stocks WHERE is_active = 1"
            ).fetchall()
        return [dict(r) for r in rows]
