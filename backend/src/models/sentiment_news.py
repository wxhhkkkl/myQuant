from backend.src.db.sqlite import get_db


class SentimentNews:
    @staticmethod
    def create_table():
        with get_db() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sentiment_news (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    stock_code    VARCHAR(10) NOT NULL,
                    title         VARCHAR(500) NOT NULL,
                    summary       TEXT,
                    source        VARCHAR(100),
                    url           VARCHAR(500),
                    pub_time      TIMESTAMP NOT NULL,
                    sentiment     VARCHAR(10),
                    fetched_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (stock_code) REFERENCES stocks(stock_code)
                )
            """)

    @staticmethod
    def insert(code: str, title: str, summary: str = None,
               source: str = None, url: str = None, pub_time: str = None,
               sentiment: str = None):
        with get_db() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO sentiment_news
                    (stock_code, title, summary, source, url, pub_time, sentiment)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (code, title, summary, source, url, pub_time, sentiment))

    @staticmethod
    def for_stock(code: str, limit: int = 20) -> list:
        with get_db() as conn:
            rows = conn.execute("""
                SELECT * FROM sentiment_news
                WHERE stock_code = ?
                ORDER BY pub_time DESC
                LIMIT ?
            """, (code, limit)).fetchall()
        return [dict(r) for r in rows]
