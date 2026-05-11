from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from backend.src.templates import templates
from backend.src.services.data_service import (
    get_stock_list, get_kline, get_financials, get_sector_info,
    get_valuation, get_news, get_stock_list_with_quotes,
    get_weekly_kline, get_monthly_kline, get_quote,
)
from backend.src.services.ai_screening import call_deepseek
from backend.src.models.stock import Stock

router = APIRouter()


@router.get("/api/stocks/search")
async def search_stocks(q: str = Query(default="", min_length=0)):
    if not q.strip():
        return []
    return Stock.search(q)


@router.get("/api/stocks/list")
async def stock_list(page: int = Query(1, ge=1), per_page: int = Query(50, ge=1, le=200),
                     sort_by: str = Query("stock_code"), sort_order: str = Query("asc"),
                     keyword: str = Query(""), watchlist_only: bool = Query(False)):
    if sort_by not in ("stock_code", "latest_price", "change_pct"):
        sort_by = "stock_code"
    if sort_order not in ("asc", "desc"):
        sort_order = "asc"
    return get_stock_list_with_quotes(page=page, per_page=per_page,
                                       sort_by=sort_by, sort_order=sort_order,
                                       keyword=keyword, watchlist_only=watchlist_only)


@router.get("/stocks", response_class=HTMLResponse)
async def stocks_page(request: Request):
    return templates.TemplateResponse(request, "pages/stocks.html")


@router.get("/stocks/table", response_class=HTMLResponse)
async def stocks_table(request: Request,
                        page: int = Query(1, ge=1), per_page: int = Query(50, ge=1, le=200),
                        sort_by: str = Query("stock_code"), sort_order: str = Query("asc"),
                        keyword: str = Query(""), watchlist_only: bool = Query(False)):
    if sort_by not in ("stock_code", "latest_price", "change_pct"):
        sort_by = "stock_code"
    if sort_order not in ("asc", "desc"):
        sort_order = "asc"
    result = get_stock_list_with_quotes(page=page, per_page=per_page,
                                         sort_by=sort_by, sort_order=sort_order,
                                         keyword=keyword, watchlist_only=watchlist_only)
    return templates.TemplateResponse(request, "components/stock_table.html", {
        "stocks": result["stocks"],
        "pagination": result["pagination"],
        "sort_by": sort_by,
        "sort_order": sort_order,
        "keyword": keyword,
        "watchlist_only": watchlist_only,
        "sort_icon": lambda field: "▲" if sort_by == field and sort_order == "asc" else ("▼" if sort_by == field and sort_order == "desc" else ""),
        "next_sort": lambda field: "desc" if sort_by != field or sort_order == "asc" else "asc",
    })


@router.get("/stocks/{code}", response_class=HTMLResponse)
async def stock_detail_page(request: Request, code: str):
    stock = Stock.get(code)
    if not stock:
        return RedirectResponse(url="/stocks")
    return templates.TemplateResponse(request, "pages/stock_detail.html", {"stock": stock})


@router.get("/stocks/{code}/kline-view", response_class=HTMLResponse)
async def stock_kline_view(request: Request, code: str):
    _stock_or_404(code)
    return templates.TemplateResponse(request, "components/stock_kline.html", {"code": code})


@router.get("/stocks/{code}/quote-view", response_class=HTMLResponse)
async def stock_quote_view(request: Request, code: str):
    _stock_or_404(code)
    quote = get_quote(code)
    from datetime import date
    return templates.TemplateResponse(request, "components/stock_quote.html", {
        "code": code, "quote": quote, "now": date.today().isoformat()
    })


@router.get("/api/stocks/{code}/kline")
async def stock_kline(code: str, start: str = None, end: str = None,
                       period: str = Query("daily")):
    from datetime import date, timedelta
    if not end:
        end = date.today().isoformat()
    if not start:
        start = (date.today() - timedelta(days=365)).isoformat()

    stock = Stock.get(code)

    if period == "weekly":
        data = get_weekly_kline(code, start, end)
    elif period == "monthly":
        data = get_monthly_kline(code, start, end)
    else:
        data = get_kline(code, start, end)

    return {
        "stock_code": code,
        "stock_name": stock["stock_name"] if stock else "",
        "period": period,
        "data": data,
    }


@router.get("/api/stocks/{code}/quote")
async def stock_quote(code: str):
    return get_quote(code)


def _stock_or_404(code: str):
    stock = Stock.get(code)
    if not stock:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Stock {code} not found")
    return stock


@router.get("/api/stocks/{code}/fundamentals", response_class=HTMLResponse)
async def fundamental_tab(request: Request, code: str):
    stock = _stock_or_404(code)
    valuation = get_valuation(code)
    return templates.TemplateResponse(request, "components/fundamentals.html", {
        "stock": stock, "valuation": valuation
    })


@router.get("/api/stocks/{code}/financials", response_class=HTMLResponse)
async def financials_tab(request: Request, code: str):
    _stock_or_404(code)
    reports = get_financials(code)
    return templates.TemplateResponse(request, "components/financials.html", {
        "reports": reports, "code": code
    })


@router.get("/api/stocks/{code}/sentiment", response_class=HTMLResponse)
async def sentiment_tab(request: Request, code: str):
    _stock_or_404(code)
    news = get_news(code)
    return templates.TemplateResponse(request, "components/sentiment.html", {
        "news": news, "code": code
    })


@router.get("/api/stocks/{code}/sector", response_class=HTMLResponse)
async def sector_tab(request: Request, code: str):
    _stock_or_404(code)
    sector = get_sector_info(code)
    return templates.TemplateResponse(request, "components/sector.html", {
        "sector": sector, "code": code
    })


@router.post("/api/stocks/ai-picks", response_class=HTMLResponse)
async def ai_picks(request: Request):
    stocks = get_stock_list()
    candidates = []
    for s in stocks[:200]:
        val = get_valuation(s["stock_code"])
        if val:
            s.update(val)
            candidates.append(s)
    recommendations = call_deepseek(candidates)
    return templates.TemplateResponse(request, "components/ai_picks.html", {
        "recommendations": recommendations
    })
