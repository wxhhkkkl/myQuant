from backend.src.db.sqlite import get_db


class Order:
    @staticmethod
    def create_table():
        with get_db() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stock_code VARCHAR(10) NOT NULL,
                    order_type VARCHAR(10) NOT NULL,
                    price REAL NOT NULL,
                    quantity INTEGER NOT NULL,
                    signal_id INTEGER,
                    status VARCHAR(20) DEFAULT 'submitted',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    @staticmethod
    def create(stock_code: str, order_type: str, price: float,
               quantity: int, signal_id: int = None) -> int:
        with get_db() as conn:
            cur = conn.execute(
                "INSERT INTO orders (stock_code, order_type, price, quantity, signal_id) "
                "VALUES (?, ?, ?, ?, ?)",
                (stock_code, order_type, price, quantity, signal_id)
            )
            return cur.lastrowid

    @staticmethod
    def get(order_id: int) -> dict | None:
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM orders WHERE id = ?", (order_id,)
            ).fetchone()
        return dict(row) if row else None

    @staticmethod
    def cancel(order_id: int):
        with get_db() as conn:
            conn.execute(
                "UPDATE orders SET status = 'cancelled' WHERE id = ?",
                (order_id,)
            )

    @staticmethod
    def all() -> list:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM orders ORDER BY created_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]
