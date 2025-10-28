from fastapi import APIRouter
import json, os
router = APIRouter()

@router.get("/api/portfolio/data")
def portfolio_data():
    f = "logs/dashboard_portfolio.json"
    if not os.path.exists(f):
        return {"positions": [], "account": {}}
    try:
        return json.load(open(f))
    except Exception as e:
        return {"error": str(e), "positions": [], "account": {}}
