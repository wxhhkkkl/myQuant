from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from backend.src.models.watchlist import Watchlist

router = APIRouter()


@router.get("/api/watchlist")
async def list_watchlist():
    return Watchlist.all()


@router.post("/api/watchlist/add")
async def add_to_watchlist(request: Request):
    data = await request.json()
    code = data.get("stock_code")
    notes = data.get("notes")
    if not code:
        return JSONResponse({"error": "stock_code required"}, status_code=400)
    Watchlist.add(code, notes)
    return {"status": "ok"}


@router.delete("/api/watchlist/{code}")
async def remove_from_watchlist(code: str):
    Watchlist.remove(code)
    return {"status": "ok"}
