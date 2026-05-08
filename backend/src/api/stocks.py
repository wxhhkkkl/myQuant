from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from backend.src.templates import templates
from backend.src.services.data_service import (
    get_stock_list, get_kline, get_financials, get_sector_info,
    get_valuation, get_news,
)
from backend.src.services.ai_screening import call_deepseek
from backend.src.models.stock import Stock

router = APIRouter()


@router.get("/api/stocks/search")
async def search_stocks(q: str = Query(default="", min_length=0)):
    if not q.strip():
        return []
    return Stock.search(q)


@router.get("/stocks", response_class=HTMLResponse)
async def stocks_page(request: Request):
    return templates.TemplateResponse(request, "pages/stocks.html")


@router.get("/stocks/{code}", response_class=HTMLResponse)
async def stock_detail_page(request: Request, code: str):
    stock = Stock.get(code)
    if not stock:
        return RedirectResponse(url="/stocks")
    return templates.TemplateResponse(request, "pages/stock_detail.html", {"stock": stock})


@router.get("/api/stocks/{code}/kline")
async def stock_kline(code: str, start: str = None, end: str = None):
    from datetime import date, timedelta
    if not end:
        end = date.today().isoformat()
    if not start:
        start = (date.today() - timedelta(days=365)).isoformat()
    data = get_kline(code, start, end)
    stock = Stock.get(code)
    return {
        "stock_code": code,
        "stock_name": stock["stock_name"] if stock else "",
        "data": data,
    }


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
