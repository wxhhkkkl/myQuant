"""Sector analysis computation engine.

Core functions for computing sector trend K-lines, detecting sector movements,
calculating heat scores, and ranking sectors by valuation.
"""
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


# --- Movement Detection ---

def detect_movements(closes: list, threshold: float = 0.10,
                     min_days: int = 5) -> list:
    """Detect uptrend runs meeting the thresholds.

    A "movement" is a contiguous interval where cumulative return >= threshold
    and duration >= min_days trading days.

    Args:
        closes: List of close prices in chronological order.
        threshold: Minimum cumulative return (default 0.10 = 10%).
        min_days: Minimum number of trading days (default 5).

    Returns:
        List of dicts with start_idx, end_idx, total_return (pct).
    """
    if len(closes) < min_days:
        return []

    movements = []
    i = 0
    n = len(closes)

    while i < n:
        found_j = -1
        # Find the EARLIEST j (not the farthest) that meets thresholds
        for j in range(i + min_days - 1, n):
            ret = (closes[j] - closes[i]) / closes[i]
            if ret >= threshold:
                found_j = j
                break
        if found_j >= 0:
            total_return = round((closes[found_j] - closes[i]) / closes[i] * 100, 2)
            movements.append({
                "start_idx": i,
                "end_idx": found_j,
                "total_return": total_return,
            })
            i = found_j + 1
        else:
            i += 1

    return movements


# --- Valuation Level ---

def calc_valuation_level(pe_median: float | None,
                         all_sectors_pe: list) -> str:
    """Compute valuation level using tertile split.

    Sectors ranked by PE median. Bottom 1/3 = 低估, Middle 1/3 = 适中,
    Top 1/3 = 高估.

    Args:
        pe_median: This sector's PE median, or None if unavailable.
        all_sectors_pe: List of all sectors' PE medians (may contain None).

    Returns:
        '高估', '适中', '低估', or '--' if PE is None.
    """
    if pe_median is None:
        return "--"

    valid = sorted([p for p in all_sectors_pe if p is not None])

    if len(valid) < 3:
        return "适中"

    # All equal → all 适中
    if valid[0] == valid[-1]:
        return "适中"

    n = len(valid)
    low_cut = n // 3
    high_cut = n - low_cut

    # Find position of pe_median in sorted list
    # Use the first index where value >= pe_median
    pos = 0
    for i, v in enumerate(valid):
        if pe_median <= v:
            pos = i
            break
    else:
        pos = n - 1

    if pos < low_cut:
        return "低估"
    elif pos >= high_cut:
        return "高估"
    else:
        return "适中"


# --- Heat Score ---

def calc_heat_score(change_pct_1w: float | None,
                    vol_change_pct: float | None,
                    up_ratio: float | None) -> float:
    """Compute composite heat score.

    Formula: change_pct_1w × 0.4 + vol_change_pct × 0.3 + up_ratio × 0.3

    Args:
        change_pct_1w: Weekly price change percentage.
        vol_change_pct: Volume change vs previous week.
        up_ratio: Fraction of stocks that rose this week (0-1).

    Returns:
        Weighted heat score.
    """
    a = change_pct_1w if change_pct_1w is not None else 0.0
    b = vol_change_pct if vol_change_pct is not None else 0.0
    c = up_ratio if up_ratio is not None else 0.0
    return round(a * 0.4 + b * 0.3 + c * 0.3, 4)


# --- Sector Trend Computation ---

def _get_sectors() -> list:
    """Get distinct industry names from all three SW levels.
    Returns list of (sector_name, sector_level) tuples.
    """
    from backend.src.db.sqlite import get_db
    with get_db() as conn:
        rows = conn.execute("""
            SELECT DISTINCT industry, '一级' FROM stocks WHERE industry IS NOT NULL AND industry != ''
            UNION
            SELECT DISTINCT sub_industry, '二级' FROM stocks WHERE sub_industry IS NOT NULL AND sub_industry != ''
            UNION
            SELECT DISTINCT sub_sub_industry, '三级' FROM stocks WHERE sub_sub_industry IS NOT NULL AND sub_sub_industry != ''
            ORDER BY 1
        """).fetchall()
    return [(r[0], r[1]) for r in rows]


def _get_sector_stock_codes(sector_name: str) -> list:
    """Get stock codes for a sector, matching across all three SW classification levels."""
    from backend.src.db.sqlite import get_db
    with get_db() as conn:
        rows = conn.execute(
            """SELECT stock_code FROM stocks
               WHERE (industry = ? OR sub_industry = ? OR sub_sub_industry = ?)
                 AND is_active = 1""",
            (sector_name, sector_name, sector_name)
        ).fetchall()
    return [r[0] for r in rows]


def compute_sector_trend(sector_name: str):
    """Compute normalized equal-weight sector trend K-line.

    Each stock's price series is normalized to start at 100, then averaged
    across all constituents per trade date.  This avoids distortion from
    stocks with vastly different absolute prices (e.g. a 132 yuan IPO
    joining a sector of 6-12 yuan stocks).
    """
    from collections import defaultdict
    from backend.src.db.duckdb import db

    codes = _get_sector_stock_codes(sector_name)

    if not codes:
        logger.warning(f"No active stocks found for sector: {sector_name}")
        return

    placeholders = ", ".join(["?"] * len(codes))
    rows = db.query(f"""
        SELECT stock_code, trade_date, open, high, low, close
        FROM daily_kline
        WHERE stock_code IN ({placeholders})
        ORDER BY stock_code, trade_date
    """, tuple(codes)).fetchall()

    # Group raw rows by stock
    stock_series = defaultdict(list)
    for r in rows:
        close_val = r[5]
        if close_val is None:
            continue
        try:
            if close_val != close_val:
                continue
        except TypeError:
            pass
        stock_series[r[0]].append((r[1], r[2], r[3], r[4], r[5]))

    # Normalize each stock to base 100, then aggregate per date
    #   norm_close[t] = close[t] / close[first] * 100
    #   sector_close[t] = mean of norm_close across stocks that have data on date t
    date_accum = defaultdict(lambda: {"o": 0.0, "h": 0.0, "l": 0.0, "c": 0.0, "n": 0})

    for code, series in stock_series.items():
        series.sort(key=lambda x: x[0])
        # Find first valid close as base
        base_close = None
        for entry in series:
            c = entry[3]
            if c and c > 0:
                base_close = c
                break
        if base_close is None:
            continue

        factor = 100.0 / base_close
        for entry in series:
            trade_date, o, h, l, c = entry
            if c is None or not (c > 0):
                continue
            try:
                if c != c:
                    continue
            except TypeError:
                pass
            # Apply same factor to OHLC for consistency
            acc = date_accum[trade_date]
            acc["o"] += (o * factor) if (o and o > 0 and o == o) else (c * factor)
            acc["h"] += (h * factor) if (h and h > 0 and h == h) else (c * factor)
            acc["l"] += (l * factor) if (l and l > 0 and l == l) else (c * factor)
            acc["c"] += c * factor
            acc["n"] += 1

    if not date_accum:
        logger.warning(f"No valid trend data for sector: {sector_name}")
        return

    conn = db.write_conn
    conn.execute("BEGIN")
    try:
        conn.execute(
            "DELETE FROM sector_trend WHERE sector_name = ?", (sector_name,)
        )

        for trade_date in sorted(date_accum.keys()):
            acc = date_accum[trade_date]
            n = acc["n"]
            if n == 0:
                continue
            conn.execute("""
                INSERT INTO sector_trend (sector_name, trade_date, open, high, low, close, stock_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (sector_name, trade_date,
                  round(acc["o"] / n, 4),
                  round(acc["h"] / n, 4),
                  round(acc["l"] / n, 4),
                  round(acc["c"] / n, 4),
                  n))

        conn.execute("COMMIT")
        logger.info(f"Sector trend computed (normalized): {sector_name} ({len(date_accum)} days)")
    except Exception:
        conn.execute("ROLLBACK")
        raise


def _get_weekly_stats(sector_name: str) -> tuple:
    """Get current week's price change, volume change, and up ratio for a sector.

    Returns (change_pct_1w, vol_change_pct, up_ratio) or (None, None, None).
    """
    from backend.src.db.duckdb import db

    row = db.query("""
        SELECT trade_date, close FROM sector_trend
        WHERE sector_name = ?
        ORDER BY trade_date DESC
        LIMIT 10
    """, (sector_name,)).fetchall()

    if len(row) < 6:
        return None, None, None

    latest_close = row[0][1]
    # ~5 trading days ago
    prev_close = row[4][1] if len(row) > 4 else row[-1][1]
    change_pct = round((latest_close - prev_close) / prev_close * 100, 2) if prev_close else None

    # Volume change: simplified — use sector_trend doesn't store volume,
    # so compute from constituent stocks
    codes = _get_sector_stock_codes(sector_name)

    up_count = 0
    total = 0
    recent_start = row[4][0] if len(row) > 4 else row[-1][0]
    recent_end = row[0][0]

    if codes:
        placeholders = ", ".join(["?"] * len(codes))
        # Count stocks with positive weekly return
        stocks = db.query(f"""
            SELECT stock_code,
                   MAX(CASE WHEN trade_date = ? THEN close END) AS latest,
                   MAX(CASE WHEN trade_date = ? THEN close END) AS prev
            FROM daily_kline
            WHERE stock_code IN ({placeholders})
              AND trade_date IN (?, ?)
            GROUP BY stock_code
        """, (recent_end, recent_start) + tuple(codes) + (recent_end, recent_start)).fetchall()

        for s in stocks:
            if s[1] and s[2] and s[2] > 0:
                total += 1
                if s[1] > s[2]:
                    up_count += 1

    up_ratio = round(up_count / total, 4) if total > 0 else None
    vol_change_pct = None  # Simplified: not computing from raw volume

    return change_pct, vol_change_pct, up_ratio


def compute_sector_heat(sector_name: str) -> tuple:
    """Compute heat score and components for a sector.

    Returns (heat_score, change_pct_1w, vol_change_pct, up_ratio).
    """
    change_pct, vol_change, up_ratio = _get_weekly_stats(sector_name)
    heat = calc_heat_score(change_pct, vol_change, up_ratio)
    return heat, change_pct, vol_change, up_ratio


def compute_sector_pe_and_movements(sector_name: str):
    """Compute PE median and movement count for a sector.

    Returns (pe_median, movement_count, constituent_count, trend_available).
    """
    from backend.src.db.sqlite import get_db
    from backend.src.db.duckdb import db

    with get_db() as conn:
        rows = conn.execute("""
            SELECT sf.pe_ratio
            FROM stock_fundamentals sf
            JOIN stocks s ON sf.stock_code = s.stock_code
            WHERE (s.industry = ? OR s.sub_industry = ? OR s.sub_sub_industry = ?)
              AND s.is_active = 1
              AND sf.snap_date = (SELECT MAX(snap_date) FROM stock_fundamentals)
              AND sf.pe_ratio IS NOT NULL
        """, (sector_name, sector_name, sector_name)).fetchall()

        constituent_count = conn.execute("""
            SELECT COUNT(*) FROM stocks
            WHERE (industry = ? OR sub_industry = ? OR sub_sub_industry = ?)
              AND is_active = 1
        """, (sector_name, sector_name, sector_name)).fetchone()[0]

    pe_values = [r[0] for r in rows if r[0] and 0 < r[0] < 500]
    pe_median = sorted(pe_values)[len(pe_values) // 2] if pe_values else None

    # Movement count from sector_trend (last 365 days)
    start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    trend_rows = db.query("""
        SELECT close FROM sector_trend
        WHERE sector_name = ? AND trade_date >= ?
        ORDER BY trade_date
    """, (sector_name, start_date)).fetchall()

    closes = [r[0] for r in trend_rows]
    movements = detect_movements(closes)
    trend_available = 1 if len(closes) >= 5 else 0

    return pe_median, len(movements), constituent_count, trend_available


def compute_all_sectors() -> str:
    """Orchestrate full sector analysis computation.

    1. Compute sector trend K-line for each of the 31 Shenwan sectors
    2. Detect movements, calculate PE, compute heat
    3. Rank sectors by heat score
    4. Compute valuation levels via tertile split
    5. Upsert all SectorSnapshot rows

    Returns the snap_date string used.
    """
    from backend.src.models.sector import SectorSnapshot

    SectorSnapshot.create_table()

    sector_entries = _get_sectors()
    snap_date = datetime.now().strftime("%Y-%m-%d")

    logger.info(f"Computing sector analysis for {len(sector_entries)} sectors...")

    # Step 1: Compute trend for each sector
    for i, (sector_name, sector_level) in enumerate(sector_entries):
        try:
            compute_sector_trend(sector_name)
            logger.info(f"[{i+1}/{len(sector_entries)}] Trend: {sector_name} ({sector_level})")
        except Exception as e:
            logger.error(f"Trend failed for {sector_name}: {e}")

    # Step 2-3: Compute PE, movements, heat for each sector
    results = []
    for i, (sector_name, sector_level) in enumerate(sector_entries):
        try:
            pe_med, move_count, const_count, trend_avail = compute_sector_pe_and_movements(sector_name)
            heat, chg_1w, vol_chg, up_r = compute_sector_heat(sector_name)
            results.append({
                "sector": sector_name,
                "sector_level": sector_level,
                "pe_median": pe_med,
                "movement_count": move_count,
                "constituent_count": const_count,
                "trend_available": trend_avail,
                "heat_score": heat,
                "change_pct_1w": chg_1w,
                "vol_change_pct": vol_chg,
                "up_ratio": up_r,
            })
            logger.info(f"[{i+1}/{len(sector_entries)}] Analysis: {sector_name} ({sector_level}) PE={pe_med}, "
                        f"moves={move_count}, heat={heat})")
        except Exception as e:
            logger.error(f"Analysis failed for {sector_name}: {e}")
            results.append({
                "sector": sector_name,
                "sector_level": sector_level,
                "pe_median": None, "movement_count": 0,
                "constituent_count": 0, "trend_available": 0,
                "heat_score": 0.0, "change_pct_1w": None,
                "vol_change_pct": None, "up_ratio": None,
            })

    # Step 4: Rank by heat and compute valuation levels
    results.sort(key=lambda x: x["heat_score"], reverse=True)
    all_pe = [r["pe_median"] for r in results]

    for rank, r in enumerate(results, 1):
        r["heat_rank"] = rank
        r["valuation_level"] = calc_valuation_level(r["pe_median"], all_pe)

    # Step 5: Upsert all
    for r in results:
        SectorSnapshot.upsert(
            sector_name=r["sector"],
            sector_level=r.get("sector_level", ""),
            snap_date=snap_date,
            pe_median=r["pe_median"],
            valuation_level=r["valuation_level"],
            movement_count_1y=r["movement_count"],
            heat_score=r["heat_score"],
            heat_rank=r["heat_rank"],
            change_pct_1w=r["change_pct_1w"],
            vol_change_pct=r["vol_change_pct"],
            up_ratio=r["up_ratio"],
            constituent_count=r["constituent_count"],
            trend_available=r["trend_available"],
        )

    logger.info(f"Sector analysis complete: {len(results)} sectors, snap_date={snap_date}")
    return snap_date


# --- Rotation Data ---

def get_rotation_data(time_range: str = "1y",
                      granularity: str = "monthly",
                      levels: list = None) -> dict:
    """Get sector rotation data: top-3 sectors per period.

    Args:
        time_range: 1m, 3m, 6m, or 1y.
        granularity: 'monthly' or 'weekly'.
        levels: Optional list of sector levels to include (e.g. ['一级', '二级']).

    Returns:
        {"periods": [...], "leaders": [{period, top3: [{sector, change_pct}]}]}
    """
    from backend.src.db.duckdb import db
    from backend.src.db.sqlite import get_db

    range_days = {"1m": 30, "3m": 90, "6m": 180, "1y": 365}
    days = range_days.get(time_range, 365)
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    if granularity == "weekly":
        date_trunc = "DATE_TRUNC('week', trade_date)"
    else:
        date_trunc = "DATE_TRUNC('month', trade_date)"

    # Build SQL with optional level filter
    filter_clause = ""
    params = [start_date]
    if levels and len(levels) > 0:
        # Get sector names matching the requested levels
        with get_db() as conn:
            placeholders = ",".join(["?" for _ in levels])
            level_rows = conn.execute(
                f"SELECT sector_name FROM sector_snapshot WHERE sector_level IN ({placeholders})",
                levels
            ).fetchall()
        level_sectors = [r[0] for r in level_rows]
        if not level_sectors:
            return {"periods": [], "leaders": []}
        sector_placeholders = ",".join(["?" for _ in level_sectors])
        filter_clause = f"AND sector_name IN ({sector_placeholders})"
        params.extend(level_sectors)

    rows = db.query(f"""
        WITH period_bounds AS (
            SELECT
                sector_name,
                {date_trunc} AS period_start,
                MIN(trade_date) AS first_date,
                MAX(trade_date) AS last_date
            FROM sector_trend
            WHERE trade_date >= ? {filter_clause}
            GROUP BY sector_name, period_start
        ),
        period_returns AS (
            SELECT
                b.sector_name,
                b.period_start,
                f.close AS first_close,
                l.close AS last_close
            FROM period_bounds b
            JOIN sector_trend f ON f.sector_name = b.sector_name AND f.trade_date = b.first_date
            JOIN sector_trend l ON l.sector_name = b.sector_name AND l.trade_date = b.last_date
        ),
        ranked AS (
            SELECT
                sector_name,
                period_start,
                (last_close - first_close) / NULLIF(first_close, 0) * 100 AS change_pct,
                ROW_NUMBER() OVER (PARTITION BY period_start ORDER BY
                    (last_close - first_close) / NULLIF(first_close, 0) * 100 DESC) AS rn
            FROM period_returns
            WHERE first_close IS NOT NULL AND first_close > 0
        )
        SELECT period_start, sector_name, change_pct
        FROM ranked
        WHERE rn <= 3
        ORDER BY period_start, rn
    """, tuple(params)).fetchall()

    # Group by period
    from collections import defaultdict
    import math
    periods_data = defaultdict(list)
    for row in rows:
        period_str = str(row[0])[:7] if granularity == "monthly" else str(row[0])[:10]
        change = row[2]
        if change is None or math.isnan(change) or math.isinf(change):
            change = 0.0
        periods_data[period_str].append({
            "sector": row[1],
            "change_pct": round(change, 2),
        })

    periods = sorted(periods_data.keys())
    leaders = [{"period": p, "top3": periods_data[p]} for p in periods]

    return {"periods": periods, "leaders": leaders}


# --- Sector Trend Query ---

def get_sector_trend(sector_name: str, period: str = "daily",
                     time_range: str = "1y") -> dict:
    """Get sector trend K-line data for ECharts.

    Args:
        sector_name: Industry name.
        period: daily, weekly, or monthly.
        time_range: 1m, 3m, 6m, or 1y.

    Returns:
        {sector_name, data: [[date, open, high, low, close], ...], stock_count}
    """
    from backend.src.db.duckdb import db

    range_days = {"1m": 30, "3m": 90, "6m": 180, "1y": 365}
    days = range_days.get(time_range, 365)
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    if period == "weekly":
        group_expr = "DATE_TRUNC('week', trade_date) AS trade_date"
    elif period == "monthly":
        group_expr = "DATE_TRUNC('month', trade_date) AS trade_date"
    else:
        group_expr = "trade_date"

    rows = db.query(f"""
        SELECT {group_expr},
               AVG(open) AS open,
               AVG(high) AS high,
               AVG(low) AS low,
               AVG(close) AS close
        FROM sector_trend
        WHERE sector_name = ? AND trade_date >= ?
        GROUP BY trade_date
        ORDER BY trade_date
    """, (sector_name, start_date)).fetchall()

    # Get latest stock count
    stock_count = 0
    trend_row = db.query("""
        SELECT stock_count FROM sector_trend
        WHERE sector_name = ? ORDER BY trade_date DESC LIMIT 1
    """, (sector_name,)).fetchone()
    if trend_row:
        stock_count = trend_row[0]

    data = [[str(r[0]), r[1], r[2], r[3], r[4]] for r in rows]

    return {
        "sector_name": sector_name,
        "data": data,
        "stock_count": stock_count,
    }


# --- Sector Constituents ---

def get_sector_constituents(sector_name: str) -> list:
    """Get constituent stocks for a sector with latest price and fundamentals.

    Returns list of dicts with code, name, latest_price, change_pct, pe_ratio, market_cap.
    """
    from backend.src.db.sqlite import get_db

    with get_db() as conn:
        rows = conn.execute("""
            SELECT s.stock_code, s.stock_name,
                   sf.pe_ratio, sf.market_cap
            FROM stocks s
            LEFT JOIN stock_fundamentals sf
              ON sf.stock_code = s.stock_code
              AND sf.snap_date = (SELECT MAX(snap_date) FROM stock_fundamentals)
            WHERE (s.industry = ? OR s.sub_industry = ? OR s.sub_sub_industry = ?)
              AND s.is_active = 1
            ORDER BY sf.market_cap DESC NULLS LAST
        """, (sector_name, sector_name, sector_name)).fetchall()

    # Get latest price + change_pct from DuckDB
    from backend.src.db.duckdb import db

    constituents = []
    for r in rows:
        code = r[0]
        kline = db.query("""
            SELECT close, trade_date FROM daily_kline
            WHERE stock_code = ?
            ORDER BY trade_date DESC LIMIT 2
        """, (code,)).fetchall()

        latest_price = kline[0][0] if kline else None
        change_pct = None
        if len(kline) >= 2 and kline[0][0] and kline[1][0] and kline[1][0] > 0:
            change_pct = round((kline[0][0] - kline[1][0]) / kline[1][0] * 100, 2)

        constituents.append({
            "stock_code": code,
            "stock_name": r[1],
            "latest_price": latest_price,
            "change_pct": change_pct,
            "pe_ratio": r[2] if r[2] and r[2] < 500 else None,
            "market_cap": r[3],
        })

    return constituents
