"""
app/routers/agentic_rag.py
Agentic RAG 정보검색 시스템 API 엔드포인트
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from app.services.agentic_rag_service import run_agentic_rag, get_mermaid_graph_definition

router = APIRouter(prefix="/api/agentic-rag", tags=["agentic-rag"])

class AgenticRAGRequest(BaseModel):
    query: str
    selected_items: Optional[List[str]] = ["기본 정보"]
    selected_model: Optional[str] = "gpt-4o"

@router.post("/query")
def process_agentic_rag(req: AgenticRAGRequest):
    """Agentic RAG 질의 처리 (Agent -> Retrieve -> Grade -> Rewrite -> Generate)"""
    result = run_agentic_rag(
        question=req.query,
        selected_items=req.selected_items,
        selected_model=req.selected_model
    )
    return result

@router.get("/graph")
def get_workflow_graph():
    """LangGraph 워크플로 시각화 Mermaid 정의 반환"""
    mermaid = get_mermaid_graph_definition()
    return {"mermaid": mermaid}
