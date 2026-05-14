"""
Download financial report data via xtdata and store in SQLite.

Fields extracted:
  - revenue:    Income.revenue_inc
  - net_profit: Income.net_profit_excl_min_int_inc (归母净利润)
  - roe:        PershareIndex.net_roe
  - debt_ratio: Balance: tot_liab / tot_assets
  - eps:        PershareIndex.s_fa_eps_basic

Usage:
  python -m backend.src.scripts.download_financials
"""
import logging
import time as _time

logger = logging.getLogger(__name__)


def _process_batch(batch_stocks, data):
    """Extract financial records from xtdata response. Returns list of tuples."""
    records = []
    for s in batch_stocks:
        code = s["stock_code"]
        if code not in data:
            continue

        tables = data[code]
        income = tables.get("Income")
        balance = tables.get("Balance")
        psi = tables.get("PershareIndex")

        if income is None or income.empty:
            continue

        # Build lookup indexes for Balance and PershareIndex by m_timetag
        bal_lookup = {}
        if balance is not None and not balance.empty:
            for _, r in balance.iterrows():
                bal_lookup[r["m_timetag"]] = r
        psi_lookup = {}
        if psi is not None and not psi.empty:
            for _, r in psi.iterrows():
                psi_lookup[r["m_timetag"]] = r

        for _, row in income.iterrows():
            period = str(int(row["m_timetag"]))
            if not period or len(period) < 8:
                continue

            rev = row.get("revenue_inc")
            net = row.get("net_profit_excl_min_int_inc")

            debt_ratio = None
            if period in bal_lookup:
                br = bal_lookup[period]
                ta = br.get("tot_assets")
                tl = br.get("tot_liab")
                if ta and ta > 0 and tl is not None:
                    debt_ratio = round(tl / ta * 100, 2)

            eps = None
            roe = None
            if period in psi_lookup:
                pr = psi_lookup[period]
                eps = pr.get("s_fa_eps_basic")
                roe = pr.get("net_roe")

            report_type = "annual" if period.endswith("1231") else "quarterly"

            records.append((
                code, period,
                float(rev) if rev and rev == rev else None,
                float(net) if net and net == net else None,
                float(roe) if roe and roe == roe else None,
                float(debt_ratio) if debt_ratio is not None else None,
                float(eps) if eps and eps == eps else None,
                report_type,
            ))

    return records


def _flush_records(records):
    """Batch insert financial records into SQLite in a single transaction."""
    if not records:
        return
    from backend.src.db.sqlite import get_db
    with get_db() as conn:
        conn.executemany("""
            INSERT OR REPLACE INTO financial_reports
                (stock_code, report_period, revenue, net_profit,
                 roe, debt_ratio, eps, report_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, records)


def download_all():
    from backend.src.models.stock import Stock
    from backend.src.models.financial_report import FinancialReport
    from backend.src.services.data_service import HAS_XTDATA

    if not HAS_XTDATA:
        logger.warning("xtquant not available; skipping financial download.")
        return

    from xtquant import xtdata

    FinancialReport.create_table()
    stocks = Stock.all_active()
    total = len(stocks)
    BATCH = 100
    total_records = 0
    t0 = _time.time()

    logger.info(f"Downloading financial reports for {total} stocks...")

    for bi in range(0, total, BATCH):
        batch = stocks[bi:bi + BATCH]
        codes = [s["stock_code"] for s in batch]

        xtdata.download_financial_data(codes)
        _time.sleep(2)
        data = xtdata.get_financial_data(codes)

        records = _process_batch(batch, data)
        _flush_records(records)
        total_records += len(records)

        done = min(bi + BATCH, total)
        elapsed = _time.time() - t0
        rate = done / elapsed if elapsed > 0 else 0
        eta = (total - done) / rate if rate > 0 else 999
        logger.info(f"  {done}/{total} stocks, {total_records} records, "
                    f"{rate:.1f} st/s, elapsed {elapsed:.0f}s, ETA {eta:.0f}s")

    logger.info(f"Financial download done: {total_records} records in {_time.time() - t0:.0f}s")


def main():
    from backend.src.models.log import setup_logging
    from backend.src.db.migrate import run_migrations

    setup_logging()
    run_migrations()
    download_all()


if __name__ == "__main__":
    main()
