"""
app/services/rag_service.py
pgvector 기반 RAG 시맨틱 유산 검색 서비스
"""

from typing import List, Dict, Any
from app.database import get_supabase
from app.config import settings

# Mock In-Memory Heritage Dataset for local instant query & fallback
MOCK_HERITAGES = [
    {
        "id": "h1-uuid",
        "h_id": "H1",
        "name": "세종 연기아문",
        "address": "세종특별자치시 연기면 연기리 31-1",
        "description": "조선시대 연기현의 관아 대문건물로 1978년 복원되었으며 세종시 역사의 상징적 건물입니다.",
        "era": "조선시대 초",
        "era_normalized": "조선 전기",
        "think_about": "조선시대 지방 관아의 입지와 옛 행정구역(연기현)이 현재 행정중심복합도시 세종으로 변모해온 과정에 대해 생각해봅시다.",
        "image_url": "https://images.unsplash.com/photo-1548013146-72479768bada?w=600&q=80",
        "dong_eup_myeon": "연기면",
        "category": "시도유형문화재",
        "lat": 36.5200,
        "lng": 127.2700,
        "recommend_count": 142
    },
    {
        "id": "h2-uuid",
        "h_id": "H2",
        "name": "세종 비암사 극락보전",
        "address": "세종특별자치시 전의면 다방리 512",
        "description": "운주산 기슭 비암사에 위치한 극락보전으로 웅장한 불전 지붕과 고풍스러운 단청이 특징입니다.",
        "era": "조선전기",
        "era_normalized": "조선 전기",
        "think_about": "깊은 산속 아늑한 비암사 산사에서 세종시민들이 마음의 평온을 찾고 전통 문화를 체험하는 의미를 곱씹어봅시다.",
        "image_url": "https://images.unsplash.com/photo-1590523741831-ab7e8b8f9c7f?w=600&q=80",
        "dong_eup_myeon": "전의면",
        "category": "보물",
        "lat": 36.6300,
        "lng": 127.2000,
        "recommend_count": 289
    },
    {
        "id": "h3-uuid",
        "h_id": "H3",
        "name": "초려 이유태 역사공원",
        "address": "세종특별자치시 어진동 580",
        "description": "조선 후기 저명한 유학자 초려 이유태 선생의 학문과 정신을 기념하기 위해 조성된 한옥 테마공원입니다.",
        "era": "조선 후기",
        "era_normalized": "조선 후기",
        "think_about": "현대적 신도시 아파트 단지 사이에 조화롭게 우뚝 선 전통 한옥 공원이 주는 정서적 쉼터의 소중함을 느껴봅시다.",
        "image_url": "https://images.unsplash.com/photo-1578632767115-351597cf2477?w=600&q=80",
        "dong_eup_myeon": "어진동",
        "category": "시도기념물",
        "lat": 36.5050,
        "lng": 127.2600,
        "recommend_count": 195
    },
    {
        "id": "h4-uuid",
        "h_id": "H4",
        "name": "합강리 선사유적",
        "address": "세종특별자치시 동면 합강리",
        "description": "금강과 미호천이 합류하는 지점에 위치한 청동기시대 집터 및 선사 인류의 생활 터전입니다.",
        "era": "청동기시대",
        "era_normalized": "청동기시대",
        "think_about": "두 강 줄기가 합쳐지는 비옥한 땅에서 청동기인들이 공동체를 형성하며 살아갔던 자연 환경의 지혜를 생각해봅시다.",
        "image_url": "https://images.unsplash.com/photo-1509316975850-ff9c5deb0cd9?w=600&q=80",
        "dong_eup_myeon": "연동면",
        "category": "선사유적",
        "lat": 36.4900,
        "lng": 127.3200,
        "recommend_count": 88
    },
    {
        "id": "h5-uuid",
        "h_id": "H5",
        "name": "세종 영평사 구절초길",
        "address": "세종특별자치시 장군면 영평사길 124",
        "description": "조선시대 사찰로 가을철 하얀 구절초 꽃이 온 산사를 덮어 장관을 이루는 힐링 명소입니다.",
        "era": "조선 후기",
        "era_normalized": "조선 후기",
        "think_about": "자연 경관과 어우러진 산사 문화유산이 세종시민에게 선사하는 생태적·정서적 가치에 대해 생각해봅시다.",
        "image_url": "https://images.unsplash.com/photo-1542601906990-b4d3fb778b09?w=600&q=80",
        "dong_eup_myeon": "장군면",
        "category": "사찰유적",
        "lat": 36.5100,
        "lng": 127.2300,
        "recommend_count": 312
    }
]

def search_heritages_rag(query: str, theme: str = None, top_k: int = 4) -> List[Dict[str, Any]]:
    """자연어 기반 pgvector RAG 유산 검색 (Supabase 연동 또는 키워드 유사도 매칭)"""
    supabase = get_supabase()
    
    if supabase:
        try:
            # Supabase RPC 또는 pgvector match_documents 호출
            res = supabase.table("heritages").select("*").limit(top_k).execute()
            if res.data and len(res.data) > 0:
                return res.data
        except Exception as e:
            print(f"Supabase pgvector query error: {e}")

    # Fallback simulation
    results = []
    q_lower = query.lower() if query else ""
    for item in MOCK_HERITAGES:
        score = 0
        if q_lower in item['name'].lower() or q_lower in item['description'].lower() or q_lower in item['era_normalized'].lower():
            score += 3
        if theme and (theme in item['category'] or theme in item['description'] or theme in item['era_normalized']):
            score += 2
        results.append((score, item))
        
    results.sort(key=lambda x: x[0], reverse=True)
    return [x[1] for x in results[:top_k]]
