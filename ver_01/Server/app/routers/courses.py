"""
app/routers/courses.py
사용자 정의 여행 코스 저장 및 조회 API
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

router = APIRouter(prefix="/api/courses", tags=["courses"])

# In-Memory User Courses Database (DB Dynamic Sync)
COURSES_DB = []

class CourseCreateRequest(BaseModel):
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    title: Optional[str] = None
    course_name: Optional[str] = None
    transport_mode: Optional[str] = None
    transport: Optional[str] = None
    total_time: Optional[str] = None
    total_time_min: Optional[Any] = None
    items: List[Dict[str, Any]]
    ai_content: Optional[str] = None

def normalize_course_record(c: Dict[str, Any]) -> Dict[str, Any]:
    c_title = c.get("title") or c.get("course_name") or "세종시 문화유산 여행 코스"
    c_user = c.get("user_id") or c.get("user_email") or "user-101"
    c_transport = c.get("transport_mode") or c.get("transport") or "승용차"
    c_time = str(c.get("total_time") or c.get("total_time_min") or c.get("total_duration_min") or "약 60분")
    
    c["title"] = c_title
    c["course_name"] = c_title
    c["user_id"] = c_user
    c["user_email"] = c_user
    c["transport_mode"] = c_transport
    c["transport"] = c_transport
    c["total_time"] = c_time
    c["total_time_min"] = c_time
    c["total_duration_min"] = c_time
    return c

@router.post("")
def create_course(req: CourseCreateRequest):
    """여행 코스 저장"""
    new_id = f"course-{len(COURSES_DB) + 1}"
    title_val = req.title or req.course_name or "세종시 문화유산 여행 코스"
    user_val = req.user_id or req.user_email or "user-101"
    transport_val = req.transport_mode or req.transport or "승용차"
    time_val = str(req.total_time or req.total_time_min or "약 60분")

    raw_course = {
        "id": new_id,
        "course_id": new_id,
        "user_id": user_val,
        "user_email": user_val,
        "title": title_val,
        "course_name": title_val,
        "transport_mode": transport_val,
        "transport": transport_val,
        "total_time": time_val,
        "total_time_min": time_val,
        "created_at": datetime.now().isoformat(),
        "items": req.items,
        "ai_content": req.ai_content or "세종 문화유산 AI 코스가 성공적으로 생성되었습니다."
    }
    new_course = normalize_course_record(raw_course)
    COURSES_DB.append(new_course)
    return {
        "message": "코스가 성공적으로 저장되었습니다.",
        "course": new_course
    }

@router.get("/{user_id}")
def get_user_courses(user_id: str):
    """특정 사용자가 만든 코스 목록 조회"""
    courses = [normalize_course_record(c) for c in COURSES_DB]
    return [c for c in courses if c["user_id"] == user_id or c["user_email"] == user_id]
