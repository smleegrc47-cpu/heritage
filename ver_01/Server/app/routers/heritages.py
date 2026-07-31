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
    dong: Optional[str] = Query(None, description="읍면동 필터 (예: 연기면, 어진동)"),
    dong_eup_myeon: Optional[str] = Query(None, description="읍면동 필터 호환용"),
    era_normalized: Optional[str] = Query(None, description="정규화 시대 필터 (예: 조선 전기, 청동기시대)"),
    era: Optional[str] = Query(None, description="시대 필터"),
    keyword: Optional[str] = Query(None, description="검색 키워드")
):
    """문화유산 목록 및 다중 조건 필터링"""
    target_dong = dong or dong_eup_myeon
    target_era = era_normalized or era
    supabase = get_supabase()
    if supabase:
        try:
            query_builder = supabase.table("heritages").select("*, images:heritage_images(*)")
            if target_dong:
                query_builder = query_builder.eq("dong", target_dong)
            if target_era:
                query_builder = query_builder.eq("era", target_era)
            if keyword:
                query_builder = query_builder.ilike("name", f"%{keyword}%")
            res = query_builder.execute()
            if res.data is not None:
                for row in res.data:
                    row["dong"] = row.get("dong") or row.get("dong_eup_myeon")
                    row["dong_eup_myeon"] = row["dong"]
                    row["thinkingPoint"] = row.get("thinking_point") or row.get("think_about")
                    row["thinking_point"] = row["thinkingPoint"]
                    row["latitude"] = row.get("latitude") or row.get("lat")
                    row["longitude"] = row.get("longitude") or row.get("lng")
                return res.data
        except Exception as e:
            print(f"Supabase fetch error: {e}")

    return []

@router.get("/stats")
def get_heritage_stats():
    """세종시 실시간 문화유산 현황 통계 요약 (읍면동별, 시대별 그래프용)"""
    supabase = get_supabase()
    heritages = []
    if supabase:
        try:
            res = supabase.table("heritages").select("*").execute()
            if res.data:
                heritages = res.data
        except Exception as e:
            print(f"Stats query error: {e}")

    total_count = len(heritages)
    era_counts = {}
    dong_counts = {}
    
    for h in heritages:
        era = h.get("era_normalized") or h.get("era") or "시대 미상"
        dong = h.get("dong") or h.get("dong_eup_myeon") or "세종특별자치시"
        era_counts[era] = era_counts.get(era, 0) + 1
        dong_counts[dong] = dong_counts.get(dong, 0) + 1

    era_chart_data = [{"era": k, "count": v} for k, v in era_counts.items()]
    dong_chart_data = [{"dong": k, "count": v} for k, v in dong_counts.items()]

    return {
        "total_count": total_count,
        "national_registered_count": total_count,
        "era_stats": era_chart_data,
        "dong_stats": dong_chart_data
    }

@router.get("/{heritage_id}")
def get_heritage_detail(heritage_id: str):
    """문화유산 단건 상세 정보 조회"""
    supabase = get_supabase()
    if supabase:
        try:
            res = supabase.table("heritages").select("*, images:heritage_images(*)").eq("id", heritage_id).execute()
            if res.data and len(res.data) > 0:
                row = res.data[0]
                row["dong"] = row.get("dong") or row.get("dong_eup_myeon")
                row["thinkingPoint"] = row.get("thinking_point") or row.get("think_about")
                return row
        except Exception as e:
            print(f"Detail query error: {e}")

    raise HTTPException(status_code=404, detail="해당 문화유산을 찾을 수 없습니다.")
