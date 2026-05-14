"""Sector analysis data models (SQLite)."""
from backend.src.db.sqlite import get_db


class SectorSnapshot:
    """Pre-computed sector analysis snapshot — one row per Shenwan first-level industry."""

    @staticmethod
    def create_table():
        with get_db() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sector_snapshot (
                    sector_name       VARCHAR(50) PRIMARY KEY,
                    sector_level      VARCHAR(10) DEFAULT '',
                    snap_date         DATE,
                    pe_median         DOUBLE,
                    valuation_level   VARCHAR(10),
                    movement_count_1y INTEGER DEFAULT 0,
                    heat_score        DOUBLE DEFAULT 0,
                    heat_rank         INTEGER,
                    change_pct_1w     DOUBLE,
                    vol_change_pct    DOUBLE,
                    up_ratio          DOUBLE,
                    constituent_count INTEGER DEFAULT 0,
                    trend_available   INTEGER DEFAULT 0
                )
            """)
            # Add sector_level column to existing table if missing
            try:
                conn.execute("ALTER TABLE sector_snapshot ADD COLUMN sector_level VARCHAR(10) DEFAULT ''")
            except Exception:
                pass

    @staticmethod
    def upsert(sector_name: str, snap_date: str, pe_median: float = None,
               valuation_level: str = None, movement_count_1y: int = 0,
               heat_score: float = 0.0, heat_rank: int = None,
               change_pct_1w: float = None, vol_change_pct: float = None,
               up_ratio: float = None, constituent_count: int = 0,
               trend_available: int = 0, sector_level: str = ""):
        with get_db() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO sector_snapshot
                    (sector_name, sector_level, snap_date, pe_median, valuation_level,
                     movement_count_1y, heat_score, heat_rank,
                     change_pct_1w, vol_change_pct, up_ratio,
                     constituent_count, trend_available)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (sector_name, sector_level, snap_date, pe_median, valuation_level,
                  movement_count_1y, heat_score, heat_rank,
                  change_pct_1w, vol_change_pct, up_ratio,
                  constituent_count, trend_available))

    @staticmethod
    def all_ordered(sort_by: str = "heat_rank", sort_order: str = "asc",
                    levels: list = None) -> list:
        """Return all snapshots ordered by the given column, optionally filtered by levels."""
        valid_cols = {"heat_rank", "valuation_level", "change_pct_1w",
                      "movement_count_1y", "sector_name"}
        col = sort_by if sort_by in valid_cols else "heat_rank"
        order = "ASC" if sort_order == "asc" else "DESC"

        with get_db() as conn:
            if levels and len(levels) > 0:
                placeholders = ",".join(["?" for _ in levels])
                rows = conn.execute(f"""
                    SELECT * FROM sector_snapshot
                    WHERE sector_level IN ({placeholders})
                    ORDER BY {col} {order}
                """, levels).fetchall()
            else:
                rows = conn.execute(f"""
                    SELECT * FROM sector_snapshot ORDER BY {col} {order}
                """).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def get(sector_name: str) -> dict | None:
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM sector_snapshot WHERE sector_name = ?",
                (sector_name,)
            ).fetchone()
        return dict(row) if row else None

    @staticmethod
    def last_update() -> str | None:
        """Return the latest snap_date across all sectors."""
        with get_db() as conn:
            row = conn.execute(
                "SELECT MAX(snap_date) FROM sector_snapshot"
            ).fetchone()
        return str(row[0]) if row and row[0] else None
