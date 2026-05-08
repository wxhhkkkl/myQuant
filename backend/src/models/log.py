import logging
import sqlite3
from datetime import datetime
from backend.src.config import DB_PATH, LOG_LEVEL


class SQLiteHandler(logging.Handler):
    def emit(self, record):
        try:
            conn = sqlite3.connect(str(DB_PATH))
            conn.execute(
                """INSERT INTO system_logs (level, module, message) VALUES (?, ?, ?)""",
                (record.levelname, record.name, self.format(record))
            )
            conn.commit()
            conn.close()
        except Exception:
            pass


def setup_logging():
    level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    handler = SQLiteHandler()
    handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    ))
    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(handler)
    # Also log to console
    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    root.addHandler(console)
    return root


def create_log_table():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS system_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            level VARCHAR(10) NOT NULL,
            module VARCHAR(50),
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
