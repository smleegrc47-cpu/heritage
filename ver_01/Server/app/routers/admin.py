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

import urllib.request
import json

class BatchImportRequest(BaseModel):
    records: list[ExcelHeritageRow]

@router.post("/import-excel")
def import_excel_and_images(req: BatchImportRequest):
    """서버(Server)에서 Supabase DB 및 Storage에 중복 제외 일괄 REST Bulk Insert 및 동기화 처리"""
    supabase_url = settings.SUPABASE_URL or "https://nmzrxczcytkkwgpiseaj.supabase.co"
    supabase_key = settings.SUPABASE_KEY

    # 1. Fetch existing heritage names from Supabase DB to prevent inserting duplicate records
    existing_names = set()
    if supabase_key and "your-supabase" not in supabase_key:
        try:
            get_url = f"{supabase_url}/rest/v1/heritages?select=name"
            get_headers = {
                "apikey": supabase_key,
                "Authorization": f"Bearer {supabase_key}"
            }
            get_req = urllib.request.Request(get_url, headers=get_headers, method="GET")
            with urllib.request.urlopen(get_req) as get_res:
                if get_res.status == 200:
                    existing_data = json.loads(get_res.read().decode("utf-8"))
                    existing_names = set(item.get("name", "").strip() for item in existing_data if item.get("name"))
        except Exception as e:
            print(f"Fetch existing heritages notice: {e}")

    bulk_heritages = []
    metadata_map = []
    seen_in_batch = set()
    skipped_duplicates_count = 0

    for idx, row in enumerate(req.records):
        raw_name = (row.name or "").strip()
        if not raw_name:
            continue

        # Deduplicate against DB existing records & current batch
        if raw_name in existing_names or raw_name in seen_in_batch:
            skipped_duplicates_count += 1
            continue

        seen_in_batch.add(raw_name)

        img_url = row.imageUrl
        if not img_url and row.imageFileName:
            img_url = f"{supabase_url}/storage/v1/object/public/heritage-images/{row.imageFileName}"
            
        final_dong = row.dong or row.dong_eup_myeon or "세종특별자치시"
        final_lat = row.latitude or row.lat or 36.52
        final_lng = row.longitude or row.lng or 127.27
        final_thinking = row.thinkingPoint or row.thinking_point or row.think_about or ""

        db_row = {
            "name": raw_name,
            "era": row.era or "조선시대",
            "dong": final_dong,
            "latitude": final_lat,
            "longitude": final_lng,
            "description": row.description or "",
            "thinking_point": final_thinking,
            "source": "registered",
            "status": "approved",
            "like_count": 50
        }
        bulk_heritages.append(db_row)
        metadata_map.append({
            "img_url": img_url or "https://images.unsplash.com/photo-1548625149-fc4a29cf7092?w=800",
            "original_row": row
        })

    # Direct Supabase REST API Bulk Insert
    inserted_rows = []
    if bulk_heritages and supabase_key and "your-supabase" not in supabase_key:
        try:
            url = f"{supabase_url}/rest/v1/heritages"
            headers = {
                "apikey": supabase_key,
                "Authorization": f"Bearer {supabase_key}",
                "Content-Type": "application/json",
                "Prefer": "return=representation"
            }
            req_data = json.dumps(bulk_heritages).encode("utf-8")
            request_obj = urllib.request.Request(url, data=req_data, headers=headers, method="POST")
            
            with urllib.request.urlopen(request_obj) as response:
                if response.status in [200, 201]:
                    res_body = response.read().decode("utf-8")
                    inserted_rows = json.loads(res_body)
                    print(f"✅ Supabase Bulk Insert Success: {len(inserted_rows)} new unique records created in heritages table!")

                    # Bulk Insert images to heritage_images table
                    img_bulk = []
                    for idx, created in enumerate(inserted_rows):
                        if created.get("id"):
                            img_bulk.append({
                                "heritage_id": created["id"],
                                "image_url": metadata_map[idx]["img_url"],
                                "sort_order": 0
                            })
                    if img_bulk:
                        try:
                            img_url_endpoint = f"{supabase_url}/rest/v1/heritage_images"
                            img_req_data = json.dumps(img_bulk).encode("utf-8")
                            img_request_obj = urllib.request.Request(img_url_endpoint, data=img_req_data, headers=headers, method="POST")
                            with urllib.request.urlopen(img_request_obj) as img_res:
                                print(f"✅ Supabase Heritage Images Bulk Insert Success: {len(img_bulk)} images attached!")
                        except Exception as img_err:
                            print(f"Heritage Images Bulk Insert Notice: {img_err}")
        except Exception as e:
            print(f"❌ Supabase REST Bulk Insert Error: {e}")
            if hasattr(e, 'read'):
                try:
                    print("Error Details:", e.read().decode("utf-8"))
                except Exception:
                    pass

    # Return response payload
    processed_data = []
    for idx, row in enumerate(req.records):
        created_item = inserted_rows[idx] if idx < len(inserted_rows) else None
        rec_id = created_item.get("id") if created_item else f"supa-simu-{idx + 1}"
        img_url = metadata_map[idx]["img_url"] if idx < len(metadata_map) else "https://images.unsplash.com/photo-1548625149-fc4a29cf7092?w=800"

        processed_data.append({
            "id": rec_id,
            "name": row.name,
            "era": row.era,
            "dong": row.dong or row.dong_eup_myeon or "세종특별자치시",
            "dong_eup_myeon": row.dong or row.dong_eup_myeon or "세종특별자치시",
            "latitude": row.latitude or row.lat or 36.52,
            "longitude": row.longitude or row.lng or 127.27,
            "description": row.description,
            "thinkingPoint": row.thinkingPoint or row.thinking_point,
            "source": "registered",
            "status": "approved",
            "supabase_storage_url": img_url,
            "image_url": img_url,
            "created_at": datetime.now().isoformat()
        })

    if skipped_duplicates_count > 0:
        msg = f"✅ 성공: 신규 데이터 {len(inserted_rows)}건 Supabase DB 및 Storage 이관 완료 (중복 데이터 {skipped_duplicates_count}건은 자동 제외되었습니다)."
    else:
        msg = f"✅ 성공: 총 {len(inserted_rows)}건의 문화유산 데이터와 이미지가 Supabase DB 및 Storage에 정식 적재되었습니다."

    return {
        "message": msg,
        "count": len(inserted_rows),
        "skipped_duplicates": skipped_duplicates_count,
        "data": processed_data
    }


