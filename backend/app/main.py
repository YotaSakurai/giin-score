from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import bills, members, scores, sessions
from app.config import settings

app = FastAPI(
    title="GiinScore API",
    description="政治家活動スコアリングダッシュボード API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(members.router, prefix="/api/v1")
app.include_router(bills.router, prefix="/api/v1")
app.include_router(scores.router, prefix="/api/v1")
app.include_router(sessions.router, prefix="/api/v1")


@app.get("/api/v1/health")
def health_check():
    return {"status": "ok"}
