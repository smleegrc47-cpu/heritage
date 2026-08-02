"""
app/main.py
세종특별자치시 AI 문화유산 플랫폼 백엔드 메인 앱
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import heritages, ai, citizen, admin, courses, transport, agentic_rag

app = FastAPI(
    title=settings.APP_NAME,
    description="세종특별자치시 문화유산 AI 분석·추천·코스 생성 및 시민 참여 플랫폼 백엔드 API",
    version="1.0.0"
)

# CORS Middleware Setup (allow_credentials=False for wildcard allow_origins to prevent CORS preflight error)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(heritages.router)
app.include_router(ai.router)
app.include_router(citizen.router)
app.include_router(admin.router)
app.include_router(courses.router)
app.include_router(transport.router)
app.include_router(agentic_rag.router)

@app.get("/")
def root():
    return {
        "status": "online",
        "app_name": settings.APP_NAME,
        "docs_url": "/docs"
    }

@app.get("/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
