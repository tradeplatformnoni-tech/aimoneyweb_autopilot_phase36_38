from fastapi import APIRouter
from ai import nlp_query

router = APIRouter()

@router.post("/api/nlp/query")
def ask(data: dict):
    q=data.get("query","")
    return nlp_query.query(q)
