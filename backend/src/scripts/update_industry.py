"""
Update stock industry classification with Shenwan first/second/third level names.

Builds stock→(industry, sub_industry, sub_sub_industry) mapping by iterating
through SW third-level indices and their constituent stocks.

Usage:
  python -m backend.src.scripts.update_industry
"""
import logging
import time as _time

logger = logging.getLogger(__name__)


def _build_index_tree():
    """Build tree: {third_code: {first_name, second_name, third_name}}."""
    import akshare as ak

    # First level: {code: name}
    first = {}
    df1 = ak.sw_index_first_info()
    for _, row in df1.iterrows():
        code = str(row.iloc[0]).replace(".SI", "")
        first[code] = str(row.iloc[1])

    # Second level: {code: {name, parent_name}}
    second = {}
    df2 = ak.sw_index_second_info()
    for _, row in df2.iterrows():
        code = str(row.iloc[0]).replace(".SI", "")
        second[code] = {"name": str(row.iloc[1]), "parent": str(row.iloc[2])}

    # Third level: {code: {name, parent_name}}
    third = {}
    df3 = ak.sw_index_third_info()
    for _, row in df3.iterrows():
        code = str(row.iloc[0]).replace(".SI", "")
        third[code] = {"name": str(row.iloc[1]), "parent": str(row.iloc[2])}

    logger.info(f"Index tree: {len(first)} L1, {len(second)} L2, {len(third)} L3")
    return first, second, third


def update_all():
    """Main entry: build industry mapping and update stocks table."""
    import akshare as ak
    from backend.src.db.sqlite import get_db

    first_map, second_map, third_map = _build_index_tree()
    logger.info(f"Building stock→industry mapping from {len(third_map)} third-level indices...")

    # Build second→first name lookup from second_map parent
    second_to_first = {}
    for code, info in second_map.items():
        parent_first = info["parent"]
        second_to_first[info["name"]] = parent_first

    # stock → {first, second, third}
    stock_industry = {}

    for idx, (third_code, third_info) in enumerate(sorted(third_map.items())):
        third_name = third_info["name"]
        second_name = third_info["parent"]
        first_name = second_to_first.get(second_name, "")

        try:
            df = ak.index_component_sw(symbol=third_code)
            if df is None or df.empty:
                continue
            for _, row in df.iterrows():
                stock_code = str(row.iloc[1]).zfill(6)
                # Determine exchange suffix
                code = stock_code + (".SH" if stock_code.startswith("6") else ".SZ")
                stock_industry[code] = {
                    "first": first_name,
                    "second": second_name,
                    "third": third_name,
                }
        except Exception as e:
            logger.warning(f"Failed to get constituents for {third_code} {third_name}: {e}")

        if (idx + 1) % 50 == 0:
            logger.info(f"  Progress: {idx + 1}/{len(third_map)} indices, "
                        f"{len(stock_industry)} stocks mapped")
        _time.sleep(0.3)

    logger.info(f"Mapped {len(stock_industry)} stocks to SW industry classification")

    # Update database
    with get_db() as conn:
        # Add sub_sub_industry column if not exists
        try:
            conn.execute("ALTER TABLE stocks ADD COLUMN sub_sub_industry VARCHAR(50)")
            logger.info("Added sub_sub_industry column")
        except Exception:
            pass  # column already exists

        updated = 0
        for code, ind in stock_industry.items():
            conn.execute("""
                UPDATE stocks
                SET industry = ?,
                    sub_industry = ?,
                    sub_sub_industry = ?
                WHERE stock_code = ?
            """, (ind["first"], ind["second"], ind["third"], code))
            updated += conn.total_changes

        logger.info(f"Updated {updated} stocks with SW industry classification")

    return len(stock_industry)


def main():
    from backend.src.models.log import setup_logging
    from backend.src.db.migrate import run_migrations

    setup_logging()
    run_migrations()
    logger.info("Starting industry classification update...")
    count = update_all()
    logger.info(f"Done. {count} stocks classified.")


if __name__ == "__main__":
    main()
