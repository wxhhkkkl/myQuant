import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Set test env vars BEFORE any backend imports
_tmp = Path(tempfile.mkdtemp())
os.environ["DB_PATH"] = str(_tmp / "test.db")
os.environ["DUCKDB_PATH"] = str(_tmp / "test.duckdb")
os.environ["DEEPSEEK_API_KEY"] = ""


def _seed_test_data():
    """Insert minimal test data so integration tests can exercise real queries."""
    from backend.src.models.stock import Stock
    from backend.src.models.quant_model import QuantModel
    from backend.src.models.fundamental import StockFundamental
    from backend.src.db.duckdb import db

    Stock.upsert("000001.SZ", "平安银行", industry="银行", sub_industry="股份制银行",
                 exchange="SZ", list_date="1991-04-03")
    StockFundamental.upsert("000001.SZ", "2025-12-31", market_cap=2500.0,
                            pe_ratio=5.2, pb_ratio=0.7, eps=1.8, high_52w=15.0, low_52w=9.5)
    QuantModel.create_table()
    QuantModel.register("ma_cross", "双均线模型", "MA5/MA20",
                        {"short": 5, "long": 20})

    db.execute("""
        INSERT INTO daily_kline (trade_date, stock_code, stock_name, open, high, low, close, volume, amount)
        VALUES
        ('2025-12-01', '000001.SZ', '平安银行', 12.0, 12.5, 11.8, 12.3, 50000000, 615000000),
        ('2025-12-02', '000001.SZ', '平安银行', 12.3, 12.8, 12.1, 12.6, 55000000, 693000000),
        ('2025-12-03', '000001.SZ', '平安银行', 12.6, 13.0, 12.4, 12.9, 60000000, 774000000)
    """)


@pytest.fixture(scope="session")
def client():
    from backend.src.main import app
    from backend.src.db.migrate import run_migrations
    from backend.src.db.duckdb_schema import init_schema

    run_migrations()
    init_schema()
    _seed_test_data()

    return TestClient(app)
