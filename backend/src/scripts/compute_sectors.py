"""
Compute sector analysis data: trend K-lines, movements, heat, valuation.

Aggregates daily_kline equal-weight per Shenwan first-level industry,
stores sector_trend in DuckDB and sector_snapshot in SQLite.

Usage:
  python -m backend.src.scripts.compute_sectors
"""
import logging

logger = logging.getLogger(__name__)


def download_all():
    from backend.src.services.sector_service import compute_all_sectors

    snap_date = compute_all_sectors()
    logger.info(f"Sector analysis done, snap_date={snap_date}")
    return snap_date


def main():
    from backend.src.models.log import setup_logging
    from backend.src.db.migrate import run_migrations
    from backend.src.db.duckdb_schema import init_schema

    setup_logging()
    run_migrations()
    init_schema()
    download_all()


if __name__ == "__main__":
    main()
