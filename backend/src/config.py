import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

DB_PATH = os.getenv("DB_PATH", str(DATA_DIR / "app.db"))
DUCKDB_PATH = os.getenv("DUCKDB_PATH", str(DATA_DIR / "market.duckdb"))
QMT_PATH = os.getenv("QMT_PATH", "")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
