import os
from pathlib import Path
from dotenv import load_dotenv

ENV = os.getenv("MYQUANT_ENV", "sim")

env_file = f".env.{ENV}"
if Path(env_file).exists():
    load_dotenv(env_file)
else:
    load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

DB_PATH = os.getenv("DB_PATH", str(DATA_DIR / "app.db"))
DUCKDB_PATH = os.getenv("DUCKDB_PATH", str(DATA_DIR / "market.duckdb"))
QMT_PATH = os.getenv("QMT_PATH", "")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

# Auto-detect broker-version xtquant Lib/site-packages path
if QMT_PATH:
    _qmt_bin = os.path.normpath(QMT_PATH)
    _lib_sp = os.path.join(_qmt_bin, "Lib", "site-packages")
    QMT_SITE_PACKAGES_PATH = _lib_sp if os.path.isdir(_lib_sp) else ""
else:
    QMT_SITE_PACKAGES_PATH = ""
