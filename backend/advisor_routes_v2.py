from fastapi import APIRouter, Request
from backend.advisor_ai import answer

router = APIRouter()

@router.post("/api/advisor")
async def post_advisor(req:Request):
    data = await req.json()
    q = data.get("question","")
    return answer(q)
