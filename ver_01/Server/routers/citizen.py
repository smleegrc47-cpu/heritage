"""
app/routers/citizen.py
시민 참여형 문화유산 발굴 제보 및 내 추천 조회 API
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

router = APIRouter(tags=["citizen"])

# In-Memory Citizen Recommendations Store (Mock & DB Sync)
CITIZEN_RECOMMENDATIONS_DB = [
    {
        "id": "cit-1",
        "name": "금남면 구 즉석 우물터",
        "photo_url": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=600&q=80",
        "lat": 36.4600,
        "lng": 127.2800,
        "address": "세종특별자치시 금남면 용포리 12",
        "reason": "옛 조선시대 금남 지방 마을 주민들의 오아시스 역할을 했던 역사적 우물터로 보존 가치가 높습니다.",
        "user_id": "user-101",
        "status": "승인",
        "recommend_count": 45,
        "submitted_at": "2026-07-15T10:30:00",
        "feedback": "담당자 현장 확인 완료: 세종시 미래유산 등록 추진 대상 지정"
    },
    {
        "id": "cit-2",
        "name": "연동면 고전 방앗간 건축물",
        "photo_url": "https://images.unsplash.com/photo-1513694203232-719a280e022f?w=600&q=80",
        "lat": 36.5300,
        "lng": 127.3100,
        "address": "세종특별자치시 연동면 내판리 45",
        "reason": "근대 1950년대 농촌 방앗간의 목조 구조와 제분 기계가 보존되어 있는 근대 생활문화유산입니다.",
        "user_id": "user-101",
        "status": "신청중",
        "recommend_count": 18,
        "submitted_at": "2026-07-20T14:15:00",
        "feedback": "전문가 현장 실사 일정 수립 중"
    }
]

class CitizenRecommendationSubmit(BaseModel):
    name: str
    photo_url: Optional[str] = "https://images.unsplash.com/photo-1548013146-72479768bada?w=600&q=80"
    lat: float
    lng: float
    address: Optional[str] = "세종특별자치시"
    reason: str
    user_id: str = "user-101"

@router.post("/api/citizen-recommendations")
def submit_citizen_recommendation(data: CitizenRecommendationSubmit):
    """시민 추천 문화유산 제보 제출 (기본 status = '신청중')"""
    new_id = f"cit-{len(CITIZEN_RECOMMENDATIONS_DB) + 1}"
    new_record = {
        "id": new_id,
        "name": data.name,
        "photo_url": data.photo_url,
        "lat": data.lat,
        "lng": data.lng,
        "address": data.address,
        "reason": data.reason,
        "user_id": data.user_id,
        "status": "신청중",
        "recommend_count": 1,
        "submitted_at": datetime.now().isoformat(),
        "feedback": "담당자 확인 대기 중"
    }
    CITIZEN_RECOMMENDATIONS_DB.append(new_record)
    return {
        "message": "시민 추천 문화유산이 성공적으로 접수되었습니다. 관리자 승인 후 공개됩니다.",
        "record": new_record
    }

@router.get("/api/citizen-recommendations")
def get_citizen_recommendations(status: Optional[str] = Query(None, description="신청중 / 승인 / 반려")):
    """시민 추천 목록 조회 (상태 필터)"""
    if status:
        return [r for r in CITIZEN_RECOMMENDATIONS_DB if r["status"] == status]
    return CITIZEN_RECOMMENDATIONS_DB

@router.get("/api/my-recommendations/{user_id}")
def get_my_recommendations(user_id: str):
    """내가 추천한 문화유산 목록 및 등재 피드백 상태 조회"""
    return [r for r in CITIZEN_RECOMMENDATIONS_DB if r["user_id"] == user_id]
