"""
app/routers/heritages.py
문화유산 목록 조회, 필터(동읍면, 시대, 키워드), 상세조회 및 시각화 통계 API
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List, Dict, Any
from app.services.rag_service import MOCK_HERITAGES
from app.database import get_supabase

router = APIRouter(prefix="/api/heritages", tags=["heritages"])

@router.get("", response_model=List[Dict[str, Any]])
def get_heritages(
    dong_eup_myeon: Optional[str] = Query(None, description="읍면동 필터 (예: 연기면, 어진동)"),
    era_normalized: Optional[str] = Query(None, description="정규화 시대 필터 (예: 조선 전기, 청동기시대)"),
    keyword: Optional[str] = Query(None, description="검색 키워드")
):
    """문화유산 목록 및 다중 조건 필터링"""
    supabase = get_supabase()
    if supabase:
        try:
            query_builder = supabase.table("heritages").select("*")
            if dong_eup_myeon:
                query_builder = query_builder.eq("dong_eup_myeon", dong_eup_myeon)
            if era_normalized:
                query_builder = query_builder.eq("era_normalized", era_normalized)
            if keyword:
                query_builder = query_builder.ilike("name", f"%{keyword}%")
            res = query_builder.execute()
            if res.data and len(res.data) > 0:
                return res.data
        except Exception as e:
            print(f"Supabase fetch error: {e}")

    # Fallback filtering logic
    filtered = MOCK_HERITAGES
    if dong_eup_myeon:
        filtered = [h for h in filtered if h["dong_eup_myeon"] == dong_eup_myeon]
    if era_normalized:
        filtered = [h for h in filtered if h["era_normalized"] == era_normalized]
    if keyword:
        k_lower = keyword.lower()
        filtered = [h for h in filtered if k_lower in h["name"].lower() or k_lower in h["description"].lower()]
        
    return filtered

@router.get("/stats")
def get_heritage_stats():
    """세종시 실시간 문화유산 현황 통계 요약 (읍면동별, 시대별 그래프용)"""
    total_count = len(MOCK_HERITAGES)
    national_registered_count = 3  # 국가등록/보물 등
    
    # 시대별 개수 집계
    era_counts = {}
    dong_counts = {}
    
    for h in MOCK_HERITAGES:
        era = h["era_normalized"]
        dong = h["dong_eup_myeon"]
        era_counts[era] = era_counts.get(era, 0) + 1
        dong_counts[dong] = dong_counts.get(dong, 0) + 1

    era_chart_data = [{"era": k, "count": v} for k, v in era_counts.items()]
    dong_chart_data = [{"dong": k, "count": v} for k, v in dong_counts.items()]

    return {
        "total_count": total_count,
        "national_registered_count": national_registered_count,
        "era_stats": era_chart_data,
        "dong_stats": dong_chart_data
    }

@router.get("/{heritage_id}")
def get_heritage_detail(heritage_id: str):
    """문화유산 단건 상세 정보 조회"""
    for h in MOCK_HERITAGES:
        if h["id"] == heritage_id or h["h_id"] == heritage_id:
            return h
    raise HTTPException(status_code=404, detail="문화유산을 찾을 수 없습니다.")
