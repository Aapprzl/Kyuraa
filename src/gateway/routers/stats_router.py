from fastapi import APIRouter, HTTPException, Request
from src.memory.usage_store import UsageStore
from src.utils.security import SecurityManager

router = APIRouter()
usage_store = UsageStore()

def verify_token(request: Request):
    cli_token = request.headers.get("X-API-Key") or request.query_params.get("token")
    srv_token = SecurityManager.get_gateway_token()
    if not cli_token or cli_token != srv_token:
        raise HTTPException(status_code=401, detail="❌ Akses dilarang: Token tidak valid.")

@router.get("/stats")
async def get_stats(request: Request):
    verify_token(request)
    return usage_store.get_totals()

@router.get("/stats/history")
async def get_stats_history(request: Request, days: int = 7):
    verify_token(request)
    return usage_store.get_daily_usage(days)

@router.get("/stats/by-model")
async def get_stats_by_model(request: Request):
    verify_token(request)
    return usage_store.get_by_model()

@router.post("/stats/clear-models")
async def clear_stats_by_models(request: Request):
    verify_token(request)
    body = await request.json()
    models = body.get("models", [])
    if not models:
        return {"deleted": 0}
    deleted = usage_store.clear_by_models(models)
    return {"deleted": deleted}
