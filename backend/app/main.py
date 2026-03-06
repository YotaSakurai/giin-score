from fastapi import Depends, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware

from app.api import bills, data_quality, members, scores, sessions
from app.config import settings
from app.database import get_db


class CacheControlMiddleware(BaseHTTPMiddleware):
    """GETリクエストに対してCache-Controlヘッダーを追加する。"""

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        response: Response = await call_next(request)
        if request.method == "GET" and response.status_code == 200:
            path = request.url.path
            if "/export/" in path:
                # CSVエクスポートはキャッシュしない
                pass
            elif "/health" in path:
                pass
            else:
                response.headers["Cache-Control"] = (
                    "public, max-age=300, stale-while-revalidate=600"
                )
        return response

app = FastAPI(
    title="GiinScore API",
    description="政治家活動スコアリングダッシュボード API",
    version="0.1.0",
)

app.add_middleware(CacheControlMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(members.router, prefix="/api/v1")
app.include_router(bills.router, prefix="/api/v1")
app.include_router(scores.router, prefix="/api/v1")
app.include_router(sessions.router, prefix="/api/v1")
app.include_router(data_quality.router, prefix="/api/v1")


@app.get("/api/v1/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "degraded", "database": "disconnected", "detail": str(e)}
