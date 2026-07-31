"""
app/routers/courses.py
사용자 정의 여행 코스 저장 및 조회 API
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

router = APIRouter(prefix="/api/courses", tags=["courses"])

# In-Memory User Courses Database
COURSES_DB = [
    {
        "id": "course-1",
        "user_id": "user-101",
        "title": "세종 조선 관아 & 한옥 쉼터 역사 탐방 코스",
        "transport_mode": "대중교통",
        "total_time": "약 2시간 30분",
        "created_at": "2026-07-22T11:00:00",
        "items": [
            {
                "heritage_id": "h1-uuid",
                "h_id": "H1",
                "name": "세종 연기아문",
                "address": "세종특별자치시 연기면 연기리 31-1",
                "image_url": "https://images.unsplash.com/photo-1548013146-72479768bada?w=600&q=80",
                "order_index": 1
            },
            {
                "heritage_id": "h3-uuid",
                "h_id": "H3",
                "name": "초려 이유태 역사공원",
                "address": "세종특별자치시 어진동 580",
                "image_url": "https://images.unsplash.com/photo-1578632767115-351597cf2477?w=600&q=80",
                "order_index": 2
            }
        ],
        "ai_content": "세종의 과거와 현재가 교차하는 특별 기행. 조선시대 연기현의 위엄을 상징하는 연기아문에서 출발하여, 어진동 한옥 공원에서 전통과 현대의 아늑한 조화를 만끽하는 힐링 유산 코스입니다."
    }
]

class CourseCreateRequest(BaseModel):
    user_id: str = "user-101"
    title: str
    transport_mode: str = "대중교통"
    total_time: str = "약 1시간 40분"
    items: List[Dict[str, Any]]
    ai_content: Optional[str] = None

@router.post("")
def create_course(req: CourseCreateRequest):
    """여행 코스 저장"""
    new_id = f"course-{len(COURSES_DB) + 1}"
    new_course = {
        "id": new_id,
        "user_id": req.user_id,
        "title": req.title,
        "transport_mode": req.transport_mode,
        "total_time": req.total_time,
        "created_at": datetime.now().isoformat(),
        "items": req.items,
        "ai_content": req.ai_content or "세종 문화유산 AI 코스가 성공적으로 생성되었습니다."
    }
    COURSES_DB.append(new_course)
    return {
        "message": "코스가 성공적으로 저장되었습니다.",
        "course": new_course
    }

@router.get("/{user_id}")
def get_user_courses(user_id: str):
    """특정 사용자가 만든 코스 목록 조회"""
    return [c for c in COURSES_DB if c["user_id"] == user_id]
