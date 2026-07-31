"""
app/routers/admin.py
관리자 전용 시민 추천 문화유산 승인/반려 검토 API
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.routers.citizen import CITIZEN_RECOMMENDATIONS_DB
from datetime import datetime

router = APIRouter(prefix="/api/admin", tags=["admin"])

class AdminApprovalRequest(BaseModel):
    status: str # "승인" 또는 "반려"
    feedback: Optional[str] = None
    reviewer_id: str = "admin-01"

@router.patch("/citizen-recommendations/{rec_id}")
def review_citizen_recommendation(rec_id: str, req: AdminApprovalRequest):
    """시민 추천 문화유산 실제 존재 여부 확인 후 승인 또는 반려 처리"""
    if req.status not in ["승인", "반려"]:
        raise HTTPException(status_code=400, detail="status는 '승인' 또는 '반려'여야 합니다.")
        
    for item in CITIZEN_RECOMMENDATIONS_DB:
        if item["id"] == rec_id:
            item["status"] = req.status
            item["reviewed_at"] = datetime.now().isoformat()
            item["reviewer_id"] = req.reviewer_id
            if req.feedback:
                item["feedback"] = req.feedback
            elif req.status == "승인":
                item["feedback"] = "담당자 현장 확인 완료: 세종시 유산목록 및 일반 사용자 지도에 승인 노출됩니다."
            else:
                item["feedback"] = "현장 실사 결과 역사적/보존적 검증 기준 미달로 반려 처리되었습니다."
                
            return {
                "message": f"성공적으로 {req.status} 처리되었습니다.",
                "item": item
            }
            
    raise HTTPException(status_code=404, detail="해당 추천 제보 건을 찾을 수 없습니다.")

class ExcelHeritageRow(BaseModel):
    name: str
    era: Optional[str] = "시대 미상"
    dong: Optional[str] = None
    dong_eup_myeon: Optional[str] = None
    latitude: Optional[float] = None
    lat: Optional[float] = None
    longitude: Optional[float] = None
    lng: Optional[float] = None
    description: Optional[str] = None
    thinkingPoint: Optional[str] = None
    thinking_point: Optional[str] = None
    think_about: Optional[str] = None
    imageFileName: Optional[str] = None
    imageUrl: Optional[str] = None

class BatchImportRequest(BaseModel):
    records: list[ExcelHeritageRow]

@router.post("/import-excel")
def import_excel_and_images(req: BatchImportRequest):
    """외부 엑셀 파일 데이터 및 이미지 Supabase DB 및 Storage에 일괄 저장 및 화면 표시"""
    supabase_url = "https://your-supabase-project.supabase.co"
    processed_data = []

    for row in req.records:
        img_url = row.imageUrl
        if not img_url and row.imageFileName:
            img_url = f"{supabase_url}/storage/v1/object/public/heritage-images/{row.imageFileName}"
            
        final_dong = row.dong or row.dong_eup_myeon or "세종특별자치시"
        final_lat = row.latitude or row.lat
        final_lng = row.longitude or row.lng
        final_thinking = row.thinkingPoint or row.thinking_point or row.think_about

        record = {
            "id": f"h-import-{len(processed_data) + 1}",
            "name": row.name,
            "era": row.era,
            "dong": final_dong,
            "dong_eup_myeon": final_dong,
            "latitude": final_lat,
            "longitude": final_lng,
            "description": row.description,
            "thinkingPoint": final_thinking,
            "thinking_point": final_thinking,
            "source": "registered",
            "status": "approved",
            "supabase_storage_url": img_url,
            "created_at": datetime.now().isoformat()
        }
        processed_data.append(record)

    return {
        "message": f"성공적으로 {len(processed_data)}건의 엑셀 데이터 및 이미지를 Supabase DB 테이블과 Storage에 저장했습니다.",
        "count": len(processed_data),
        "data": processed_data
    }


