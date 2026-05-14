import logging
import sys
from datetime import datetime

import requests

from backend.src.db.duckdb import db
from backend.src.db.sqlite import get_db
from backend.src.config import QMT_PATH, QMT_SITE_PACKAGES_PATH

logger = logging.getLogger(__name__)

# Add QMT path to Python path so xtquant can be found
if QMT_PATH:
    import os as _os
    qmt_path = _os.path.normpath(QMT_PATH)
    if qmt_path not in sys.path:
        sys.path.append(qmt_path)
    # Some QMT installs have xtquant inside a sub-directory
    alt_path = _os.path.join(qmt_path, "xtquant")
    if _os.path.isdir(alt_path) and alt_path not in sys.path:
        sys.path.append(alt_path)

# Broker versions put xtquant in Lib/site-packages
# Use append (not insert) so the venv's packages take priority over QMT's bundled dependencies
if QMT_SITE_PACKAGES_PATH:
    if QMT_SITE_PACKAGES_PATH not in sys.path:
        sys.path.append(QMT_SITE_PACKAGES_PATH)

# Optional imports — QMT xtdata may not be installed
try:
    from xtquant import xtdata
    HAS_XTDATA = True
except ImportError:
    xtdata = None
    HAS_XTDATA = False
    logger.warning("xtquant not available; xtdata features disabled.")

try:
    import akshare as ak
    HAS_AKSHARE = True
except ImportError:
    ak = None
    HAS_AKSHARE = False
    logger.warning("akshare not available; supplement features disabled.")


def _ensure_xtdata():
    if not HAS_XTDATA:
        raise RuntimeError("xtquant is not installed.")


def get_stock_list() -> list:
    """Return all A-share stocks with stock_code and stock_name."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT stock_code, stock_name FROM stocks WHERE is_active = 1"
        ).fetchall()
    return [dict(r) for r in rows]


def get_kline(code: str, start: str, end: str) -> list:
    """Get daily K-line data for a stock in date range. Returns list of dicts."""
    if start > end:
        raise ValueError(f"start date {start} > end date {end}")

    rows = db.query("""
        SELECT trade_date, open, high, low, close, volume, amount
        FROM daily_kline
        WHERE stock_code = ? AND trade_date BETWEEN ? AND ?
        ORDER BY trade_date
    """, (code, start, end)).fetchall()

    return [
        {"trade_date": str(r[0]), "open": r[1], "high": r[2],
         "low": r[3], "close": r[4], "volume": r[5], "amount": r[6]}
        for r in rows
    ]


def get_financials(code: str) -> list:
    """Get financial reports grouped by year with annual/quarterly hierarchy."""
    from collections import defaultdict
    with get_db() as conn:
        rows = conn.execute("""
            SELECT report_period, revenue, net_profit, roe, debt_ratio, eps, report_type
            FROM financial_reports
            WHERE stock_code = ?
            ORDER BY report_period DESC
            LIMIT 24
        """, (code,)).fetchall()
    reports = [dict(r) for r in rows]

    years = defaultdict(lambda: {"annual": None, "quarters": []})
    for r in reports:
        period = r["report_period"]
        year = period[:4]
        if r["report_type"] == "annual":
            years[year]["annual"] = r
        else:
            years[year]["quarters"].append(r)

    result = []
    for year in sorted(years.keys(), reverse=True):
        entry = {
            "year": year,
            "annual": years[year]["annual"],
            "quarters": sorted(years[year]["quarters"], key=lambda x: x["report_period"], reverse=True),
        }
        result.append(entry)
    return result


def get_sector_info(code: str) -> dict:
    """Get industry/sector classification for a stock."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT industry, sub_industry, sub_sub_industry FROM stocks WHERE stock_code = ?",
            (code,)
        ).fetchone()
    if row:
        return {"industry": row["industry"], "sub_industry": row["sub_industry"],
                "sub_sub_industry": row["sub_sub_industry"], "stock_code": code}
    return None


def get_same_industry_stocks(industry: str, limit: int = 40) -> list:
    """Get stocks in the same industry (matches across all three SW levels)."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT s.stock_code, s.stock_name, s.sub_industry, s.sub_sub_industry
            FROM stocks s
            WHERE (s.industry = ? OR s.sub_industry = ? OR s.sub_sub_industry = ?)
              AND s.is_active = 1
            LIMIT ?
        """, (industry, industry, industry, limit)).fetchall()
    return [dict(r) for r in rows]


def get_sector_list(sort_by: str = "heat_rank", sort_order: str = "asc",
                    levels: list = None) -> list:
    """Get all sector snapshots for the overview table.

    Falls back gracefully when no snapshot data exists (returns empty list).
    """
    from backend.src.models.sector import SectorSnapshot
    try:
        return SectorSnapshot.all_ordered(sort_by=sort_by, sort_order=sort_order,
                                          levels=levels)
    except Exception:
        return []


def get_valuation(code: str) -> dict:
    """Get PE/PB/valuation snapshot for a stock."""
    with get_db() as conn:
        row = conn.execute("""
            SELECT pe_ratio, pb_ratio, market_cap, eps, high_52w, low_52w
            FROM stock_fundamentals
            WHERE stock_code = ?
            ORDER BY snap_date DESC LIMIT 1
        """, (code,)).fetchone()
    if not row:
        return None
    d = dict(row)
    if d.get('pe_ratio') and d['pe_ratio'] > 500:
        d['pe_ratio'] = None
    return d


def get_industry_list() -> list:
    """Return distinct first-level industries from the stocks table."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT DISTINCT industry FROM stocks WHERE industry IS NOT NULL AND industry != '' ORDER BY industry"
        ).fetchall()
    return [r["industry"] for r in rows]


def get_stock_list_with_quotes(page=1, per_page=50, sort_by='stock_code',
                                sort_order='asc', keyword='', watchlist_only=False,
                                industry=''):
    """Return paginated stock list with latest price and change% from DuckDB."""
    # 1. Get all active stock codes (or filtered by keyword/watchlist)
    with get_db() as conn:
        where_clauses = []
        params = []
        if watchlist_only:
            where_clauses.append("stock_code IN (SELECT stock_code FROM watchlist)")
        else:
            where_clauses.append("is_active = 1")
        if keyword:
            where_clauses.append("(stock_code LIKE ? OR stock_name LIKE ?)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        if industry:
            where_clauses.append("industry = ?")
            params.append(industry)

        where_sql = " AND ".join(where_clauses)
        count_sql = f"SELECT COUNT(*) FROM stocks WHERE {where_sql}"
        total = conn.execute(count_sql, params).fetchone()[0]

        offset = (page - 1) * per_page
        rows = conn.execute(
            f"SELECT stock_code, stock_name, industry, exchange, is_active "
            f"FROM stocks WHERE {where_sql} ORDER BY stock_code "
            f"LIMIT ? OFFSET ?",
            params + [per_page, offset]
        ).fetchall()
        stocks = [dict(r) for r in rows]

    if not stocks:
        return {"stocks": [], "pagination": {"page": page, "per_page": per_page, "total": total, "total_pages": max(1, (total + per_page - 1) // per_page)}}

    # 2. Get latest prices from DuckDB for visible stock codes
    codes = [s['stock_code'] for s in stocks]
    placeholders = ','.join(['?' for _ in codes])
    price_rows = db.query(f"""
        WITH latest AS (
            SELECT stock_code, close, trade_date,
                   ROW_NUMBER() OVER (PARTITION BY stock_code ORDER BY trade_date DESC) AS rn
            FROM daily_kline
            WHERE stock_code IN ({placeholders})
        )
        SELECT l.stock_code, l.close AS latest_price, l.trade_date,
               prev.close AS prev_close
        FROM latest l
        LEFT JOIN daily_kline prev
          ON l.stock_code = prev.stock_code
         AND prev.trade_date = (
             SELECT MAX(trade_date) FROM daily_kline
             WHERE stock_code = l.stock_code AND trade_date < l.trade_date
         )
        WHERE l.rn = 1
    """, codes).fetchall()
    price_map = {}
    for r in price_rows:
        prev = r[3] if r[3] and r[3] != 0 else None
        chg_pct = round((r[1] - prev) / prev * 100, 2) if prev and r[1] else None
        price_map[r[0]] = {"latest_price": r[1], "change_pct": chg_pct}

    # 3. Get fundamentals and watchlist for visible codes
    fund_map = {}
    wl_codes = set()
    with get_db() as conn:
        fund_rows = conn.execute(f"""
            SELECT sf.stock_code, sf.pe_ratio, sf.dividend_yield, sf.book_value_per_share
            FROM stock_fundamentals sf
            WHERE sf.stock_code IN ({placeholders})
            AND sf.snap_date = (
                SELECT MAX(snap_date) FROM stock_fundamentals WHERE stock_code = sf.stock_code
            )
        """, codes).fetchall()
        for r in fund_rows:
            fund_map[r[0]] = {"pe_ratio": r[1], "dividend_yield": r[2], "book_value_per_share": r[3]}

        wl_rows = conn.execute(
            f"SELECT stock_code FROM watchlist WHERE stock_code IN ({placeholders})",
            codes
        ).fetchall()
        wl_codes = {r[0] for r in wl_rows}

    # 4. Merge and sort
    result = []
    for s in stocks:
        px = price_map.get(s['stock_code'], {})
        fund = fund_map.get(s['stock_code'], {})
        result.append({
            "stock_code": s['stock_code'],
            "stock_name": s['stock_name'],
            "industry": s.get('industry', ''),
            "latest_price": px.get("latest_price"),
            "change_pct": px.get("change_pct"),
            "pe_ratio": fund.get("pe_ratio") if fund.get("pe_ratio") and fund["pe_ratio"] < 500 else None,
            "dividend_yield": fund.get("dividend_yield"),
            "book_value_per_share": fund.get("book_value_per_share"),
            "in_watchlist": s['stock_code'] in wl_codes,
            "is_active": s.get('is_active', 1),
        })

    # Sort by the requested field
    sort_key_map = {
        "stock_code": lambda x: x["stock_code"],
        "latest_price": lambda x: x["latest_price"] or 0,
        "change_pct": lambda x: x["change_pct"] if x["change_pct"] is not None else float('-inf'),
    }
    key_fn = sort_key_map.get(sort_by, sort_key_map["stock_code"])
    reverse = sort_order == "desc"
    result.sort(key=key_fn, reverse=reverse)

    return {
        "stocks": result,
        "pagination": {
            "page": page, "per_page": per_page, "total": total,
            "total_pages": max(1, (total + per_page - 1) // per_page),
        }
    }


def get_weekly_kline(code: str, start: str, end: str) -> list:
    """Get weekly K-line aggregated from daily_kline."""
    rows = db.query("""
        SELECT
            date_trunc('week', trade_date)::DATE AS trade_date,
            stock_code,
            FIRST(open ORDER BY trade_date) AS open,
            MAX(high) AS high,
            MIN(low) AS low,
            LAST(close ORDER BY trade_date) AS close,
            SUM(volume) AS volume,
            SUM(amount) AS amount
        FROM daily_kline
        WHERE stock_code = ? AND trade_date BETWEEN ? AND ?
        GROUP BY date_trunc('week', trade_date), stock_code
        ORDER BY trade_date
    """, (code, start, end)).fetchall()

    return [
        {"trade_date": str(r[0]), "open": r[1], "high": r[2],
         "low": r[3], "close": r[4], "volume": r[5], "amount": r[6]}
        for r in rows
    ]


def get_monthly_kline(code: str, start: str, end: str) -> list:
    """Get monthly K-line aggregated from daily_kline."""
    rows = db.query("""
        SELECT
            date_trunc('month', trade_date)::DATE AS trade_date,
            stock_code,
            FIRST(open ORDER BY trade_date) AS open,
            MAX(high) AS high,
            MIN(low) AS low,
            LAST(close ORDER BY trade_date) AS close,
            SUM(volume) AS volume,
            SUM(amount) AS amount
        FROM daily_kline
        WHERE stock_code = ? AND trade_date BETWEEN ? AND ?
        GROUP BY date_trunc('month', trade_date), stock_code
        ORDER BY trade_date
    """, (code, start, end)).fetchall()

    return [
        {"trade_date": str(r[0]), "open": r[1], "high": r[2],
         "low": r[3], "close": r[4], "volume": r[5], "amount": r[6]}
        for r in rows
    ]


# --- Batch stock update state ---
import threading

_update_status = {"running": False, "total": 0, "success": 0, "fail": 0, "failed_codes": []}


def get_update_status() -> dict:
    return dict(_update_status)


def run_stock_update():
    """Background thread: download and upsert all A-share stock basic info."""
    if _update_status["running"]:
        return

    _update_status["running"] = True
    _update_status["total"] = 0
    _update_status["success"] = 0
    _update_status["fail"] = 0
    _update_status["failed_codes"] = []

    try:
        _ensure_xtdata()
        stocks = xtdata.get_stock_list_in_sector("沪深A股")
        _update_status["total"] = len(stocks)

        for code in stocks:
            try:
                info = xtdata.get_instrument_detail(code)
                name = info.get("InstrumentName", info.get("StockName", "")) if info else ""
                industry = info.get("Industry", "") if info else ""
                exchange = "SH" if code.startswith("6") else "SZ"
                list_date = info.get("ListDate", None) if info else None
                from backend.src.models.stock import Stock
                Stock.upsert(code, name, industry=industry, exchange=exchange, list_date=str(list_date) if list_date else None)
                _update_status["success"] += 1
            except Exception:
                _update_status["fail"] += 1
                _update_status["failed_codes"].append(code)
    finally:
        _update_status["running"] = False


def get_quote(code: str) -> dict:
    """Get latest market quote for a stock.

    Tries xtdata first for real-time data, falls back to latest daily_kline.
    """
    # Try xtdata real-time quote
    if HAS_XTDATA:
        try:
            data = xtdata.get_market_data(
                field_list=['open', 'high', 'low', 'lastClose', 'lastPrice',
                            'volume', 'amount'],
                stock_list=[code],
                period='1d',
                start_time='',
                count=2
            )
            if data and code in data and len(data[code]) > 0:
                # xtdata returns dict of DataFrames keyed by field
                import pandas as pd
                last_price = float(data['lastPrice'].iloc[-1, 0]) if 'lastPrice' in data else None
                pre_close = float(data['lastClose'].iloc[-1, 0]) if 'lastClose' in data else None
                open_px = float(data['open'].iloc[-1, 0]) if 'open' in data else None
                high = float(data['high'].iloc[-1, 0]) if 'high' in data else None
                low = float(data['low'].iloc[-1, 0]) if 'low' in data else None
                volume = int(data['volume'].iloc[-1, 0]) if 'volume' in data else None
                amount = float(data['amount'].iloc[-1, 0]) if 'amount' in data else None

                if last_price and pre_close and pre_close != 0:
                    change_pct = round((last_price - pre_close) / pre_close * 100, 2)
                    change_amount = round(last_price - pre_close, 2)
                else:
                    change_pct = None
                    change_amount = None

                trade_date = str(data.index[-1]) if hasattr(data, 'index') and len(data.index) > 0 else None

                return {
                    "stock_code": code,
                    "latest_price": last_price,
                    "change_pct": change_pct,
                    "change_amount": change_amount,
                    "open": open_px,
                    "high": high,
                    "low": low,
                    "pre_close": pre_close,
                    "volume": volume,
                    "amount": amount,
                    "trade_date": trade_date,
                }
        except Exception as e:
            logger.warning(f"xtdata quote failed for {code}: {e}")

    # Fallback to latest daily_kline
    row = db.query("""
        SELECT trade_date, open, high, low, close, volume, amount
        FROM daily_kline
        WHERE stock_code = ?
        ORDER BY trade_date DESC LIMIT 1
    """, (code,)).fetchone()

    if not row:
        return {
            "stock_code": code, "latest_price": None,
            "change_pct": None, "change_amount": None,
            "open": None, "high": None, "low": None,
            "pre_close": None, "volume": None, "amount": None,
            "trade_date": None,
        }

    pre_row = db.query("""
        SELECT close FROM daily_kline
        WHERE stock_code = ? AND trade_date < ?
        ORDER BY trade_date DESC LIMIT 1
    """, (code, str(row[0]))).fetchone()

    pre_close = pre_row[0] if pre_row else None
    price = row[4]
    if price and pre_close and pre_close != 0:
        change_pct = round((price - pre_close) / pre_close * 100, 2)
        change_amount = round(price - pre_close, 2)
    else:
        change_pct = None
        change_amount = None

    return {
        "stock_code": code,
        "latest_price": price,
        "change_pct": change_pct,
        "change_amount": change_amount,
        "open": row[1],
        "high": row[2],
        "low": row[3],
        "pre_close": pre_close,
        "volume": row[5],
        "amount": row[6],
        "trade_date": str(row[0]),
    }


def get_kline_date_range() -> dict:
    """Get overall K-line data date range across all stocks."""
    row = db.query("""
        SELECT MIN(trade_date), MAX(trade_date), COUNT(DISTINCT stock_code)
        FROM daily_kline
    """).fetchone()
    if row and row[0]:
        return {"min_date": str(row[0]), "max_date": str(row[1]), "stock_count": row[2]}
    return {"min_date": None, "max_date": None, "stock_count": 0}


# --- Batch K-line update state ---
_kline_update_status = {"running": False, "message": ""}


def get_kline_update_status() -> dict:
    return dict(_kline_update_status)


def run_kline_update(start_date: str, end_date: str):
    """Background thread: download K-line for all active stocks in date range."""
    if _kline_update_status["running"]:
        return

    _kline_update_status["running"] = True
    _kline_update_status["message"] = f"正在下载 {start_date} ~ {end_date} K线数据..."

    try:
        from backend.src.scripts.download_kline import download_all
        download_all(start_date, end_date)
    except Exception as e:
        logger.error(f"K-line update failed: {e}")
        _kline_update_status["message"] = f"更新失败: {e}"
    finally:
        _kline_update_status["running"] = False


def get_news(code: str, limit: int = 20) -> list:
    """Get sentiment news for a stock."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT id, title, summary, source, pub_time, sentiment, url
            FROM sentiment_news
            WHERE stock_code = ?
            ORDER BY pub_time DESC
            LIMIT ?
        """, (code, limit)).fetchall()
    return [dict(r) for r in rows]


def _fetch_guba_posts(code_short: str) -> list[dict]:
    """Fetch recent guba forum posts for a stock from East Money.

    Returns list of dicts with keys: title, pub_time, user_nickname, click_count.
    """
    import json as _json
    import re as _re
    try:
        r = requests.get(
            f"https://guba.eastmoney.com/list,{code_short},f_1.html",
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        )
        r.encoding = "utf-8"
        match = _re.search(r"var article_list=(\{.*?\});\s*var", r.text, _re.DOTALL)
        if not match:
            return []
        data = _json.loads(match.group(1))
        posts = []
        for p in data.get("re", []):
            if str(p.get("stockbar_code", "")) != code_short:
                continue
            if p.get("post_type") != 0:  # user posts only, skip news reposts
                continue
            title = p.get("post_title", "")
            if not title or title.startswith("$"):
                continue
            posts.append({
                "title": title[:200],
                "pub_time": p.get("post_publish_time", ""),
                "user_nickname": p.get("user_nickname", ""),
                "click_count": p.get("post_click_count", 0),
                "comment_count": p.get("post_comment_count", 0),
                "post_id": p.get("post_id", ""),
            })
        return posts
    except Exception as e:
        logger.warning(f"Failed to fetch guba posts for {code_short}: {e}")
        return []


def analyze_stock_sentiment(code: str) -> dict:
    """Collect news and guba posts, save to DB, and analyze sentiment via DeepSeek.

    Returns dict with news_sentiment, comment_sentiment, news_items, and guba_posts.
    """
    from datetime import date, timedelta
    from backend.src.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL
    from backend.src.models.sentiment_news import SentimentNews

    if not DEEPSEEK_API_KEY:
        return {"error": "DeepSeek API Key 未配置", "news_sentiment": None, "comment_sentiment": None}

    cutoff = (date.today() - timedelta(days=7)).isoformat()
    code_short = code.replace(".SH", "").replace(".SZ", "")

    # 1. Fetch news from akshare and save to DB
    news_for_display = []
    if HAS_AKSHARE:
        try:
            import akshare as ak
            df = ak.stock_news_em(symbol=code_short)
            if df is not None and not df.empty:
                cols = list(df.columns)
                logger.info(f"akshare stock_news_em columns for {code_short}: {cols}")

                def _col(row, names, fallback_idx):
                    for n in names:
                        if n in cols:
                            v = row.get(n)
                            return str(v) if v is not None and str(v) != "nan" else ""
                    try:
                        v = row.iloc[fallback_idx]
                        return str(v) if v is not None and str(v) != "nan" else ""
                    except (IndexError, AttributeError):
                        return ""

                now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for _, row in df.head(10).iterrows():
                    title = _col(row, ["标题", "title", "名称"], 1)
                    content = _col(row, ["内容", "content", "摘要"], 2)
                    pub_time = _col(row, ["发布时间", "pub_time", "时间"], 3)
                    source = _col(row, ["来源", "source"], 4)
                    url = _col(row, ["链接", "url", "网址"], 5)
                    if title:
                        pt = pub_time or now_ts
                        SentimentNews.insert(code, title, content[:500] or None,
                                             source or None,
                                             url or None,
                                             pt)
                        news_for_display.append({
                            "title": title, "summary": content[:200],
                            "pub_time": pt, "source": source, "url": url,
                        })
        except Exception as e:
            logger.warning(f"Failed to fetch news for {code}: {e}")

    # 2. Fetch guba forum posts and save to DB
    guba_posts = _fetch_guba_posts(code_short)
    guba_posts = [p for p in guba_posts if p["pub_time"] >= cutoff]
    for p in guba_posts:
        SentimentNews.insert(code, p["title"], None, f"股吧网友·{p['user_nickname']}",
                             None, p["pub_time"])

    # 3. Load existing news from DB (including just-saved ones)
    with get_db() as conn:
        db_rows = conn.execute("""
            SELECT title, summary, pub_time, source, url FROM sentiment_news
            WHERE stock_code = ? AND pub_time >= ?
            ORDER BY pub_time DESC LIMIT 30
        """, (code, cutoff)).fetchall()
    db_news = [{
        "title": r[0], "summary": r[1] or "", "pub_time": str(r[2]),
        "source": r[3] or "", "url": r[4] or "",
    } for r in db_rows]

    # Merge: prefer akshare-fetched items (have richer data), supplement with DB
    seen_titles = {n["title"] for n in news_for_display}
    for n in db_news:
        if n["title"] not in seen_titles:
            news_for_display.append(n)
            seen_titles.add(n["title"])

    if not news_for_display and not guba_posts:
        return {"error": "最近一周暂无新闻或评论数据", "news_sentiment": None, "comment_sentiment": None,
                "news_items": [], "guba_posts": []}

    # 4. Build prompt for DeepSeek
    prompt_parts = [
        "你是一个专业的A股市场情绪分析师。请基于以下信息，分别对【新闻报道倾向】和【网友评论倾向】给出评分。",
        "",
        "评分标准（-10到+10的整数）：",
        "  -10 ~ -7：强烈卖出/看空信号",
        "  -6 ~ -3：偏卖出/偏空",
        "  -2 ~ +2：中性/无明显倾向",
        "  +3 ~ +6：偏买入/偏多",
        "  +7 ~ +10：强烈买入/看多信号",
        "",
    ]
    if news_for_display:
        prompt_parts.append("=== 近期新闻 ===")
        for i, n in enumerate(news_for_display[:10]):
            text = f"[{n['pub_time']}] {n['title']}"
            if n.get("summary"):
                text += f" — {n['summary'][:150]}"
            prompt_parts.append(f"{i + 1}. {text}")
        prompt_parts.append("")
    if guba_posts:
        prompt_parts.append("=== 股吧网友评论 ===")
        for i, p in enumerate(guba_posts[:15]):
            prompt_parts.append(f"{i + 1}. [{p['pub_time']}] {p['user_nickname']}: {p['title']}")
        prompt_parts.append("")

    prompt_parts.extend([
        '请返回JSON（不要包含markdown代码块）：',
        '{',
        '  "news_sentiment": {"score": 数字, "label": "强烈买入/偏买入/中性/偏卖出/强烈卖出", "summary": "一句话总结新闻倾向"},',
        '  "comment_sentiment": {"score": 数字, "label": "强烈看多/偏多/中性/偏空/强烈看空", "summary": "一句话总结网友讨论倾向"}',
        '}',
    ])
    prompt = "\n".join(prompt_parts)

    # 5. Call DeepSeek
    try:
        from openai import OpenAI
        client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=1024,
        )
        content = response.choices[0].message.content
    except Exception as e:
        logger.error(f"DeepSeek API error for {code}: {e}")
        return {"error": f"DeepSeek API 调用失败: {e}", "news_sentiment": None, "comment_sentiment": None,
                "news_items": news_for_display, "guba_posts": guba_posts}

    # 6. Parse response
    import json
    try:
        data = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        try:
            if "```json" in content:
                start = content.index("```json") + 7
                end = content.index("```", start)
                data = json.loads(content[start:end])
            elif "```" in content:
                start = content.index("```") + 3
                end = content.index("```", start)
                data = json.loads(content[start:end])
            else:
                brace_start = content.find('{')
                brace_end = content.rfind('}') + 1
                if brace_start >= 0 and brace_end > brace_start:
                    data = json.loads(content[brace_start:brace_end])
                else:
                    raise ValueError("No JSON found")
        except (ValueError, json.JSONDecodeError) as e2:
            logger.warning(f"Failed to parse sentiment response for {code}: {content[:200]}")
            return {"error": "AI 返回解析失败，请重试", "news_sentiment": None, "comment_sentiment": None,
                    "news_items": news_for_display, "guba_posts": guba_posts,
                    "raw_response": content[:500]}

    result = {
        "news_sentiment": data.get("news_sentiment"),
        "comment_sentiment": data.get("comment_sentiment"),
        "news_items": news_for_display,
        "guba_posts": guba_posts,
        "error": None,
    }
    # Save to cache for future visits
    from backend.src.models.sentiment_news import SentimentCache
    SentimentCache.save(code, result)
    return result
