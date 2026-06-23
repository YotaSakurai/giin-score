from fastapi import Depends, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware

from app.api import bills, data_quality, members, reviews, scores, sessions, sleeping
from app.config import settings
from app.database import get_db

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])


class CacheControlMiddleware(BaseHTTPMiddleware):
    """GETリクエストに対してCache-Controlヘッダーを追加する。"""

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        response: Response = await call_next(request)
        if request.method == "GET" and response.status_code == 200:
            path = request.url.path
            if "/export/" in path:
                # CSVエクスポートはキャッシュしない
                pass
            elif "/reviews" in path or "/review-summary" in path:
                # レビュー系はキャッシュしない
                pass
            elif "/health" in path:
                pass
            elif "/by-party" in path or "/party-trend" in path:
                # 政党統計 - 集計結果なので長めにキャッシュ
                response.headers["Cache-Control"] = (
                    "public, max-age=3600, stale-while-revalidate=7200"
                )
            elif "/ranking" in path or "/stats" in path:
                # ランキング・統計 - 中程度
                response.headers["Cache-Control"] = (
                    "public, max-age=1800, stale-while-revalidate=3600"
                )
            elif "/data-quality" in path:
                # データ品質 - 頻繁に変わらない
                response.headers["Cache-Control"] = (
                    "public, max-age=3600, stale-while-revalidate=7200"
                )
            elif "/members/" in path and "/speeches" not in path:
                # 議員詳細 - 中程度
                response.headers["Cache-Control"] = (
                    "public, max-age=600, stale-while-revalidate=1200"
                )
            else:
                response.headers["Cache-Control"] = (
                    "public, max-age=300, stale-while-revalidate=600"
                )
        return response


API_DESCRIPTION = """
# GiinScore API

国会の公開データに基づく議員活動スコアリングAPIです。

## 概要

- **議員情報** – 議員プロフィール・スコア詳細・発言履歴・投票記録
- **スコア** – ランキング・統計・政党別比較・CSVエクスポート
- **法案** – 法案一覧・詳細・投票結果
- **会期** – 国会会期情報
- **データ品質** – 会期ごとのデータ充足状況

## スコアリング

5軸スコア（0-100、パーセンタイルランク正規化）:
- **立法活動 (LAS)** – 法案発議・委員会質疑
- **投票行動 (VBS)** – 投票参加率
- **政策影響力 (PIS)** – 成立法案への貢献
- **透明性 (TS)** – 公開活動参加度
- **質問品質 (QQS)** – 国会質問のLLM分析による品質評価

総合スコア = LAS×0.25 + VBS×0.20 + PIS×0.20 + TS×0.15 + QQS×0.20

## レート制限

APIリクエストは **60リクエスト/分** に制限されています。
`X-RateLimit-Limit`, `X-RateLimit-Remaining` ヘッダーで残り回数を確認できます。
"""

app = FastAPI(
    title="GiinScore API",
    description=API_DESCRIPTION,
    version="1.0.0",
    openapi_tags=[
        {
            "name": "members",
            "description": "議員の情報・スコア・発言・投票に関するエンドポイント",
        },
        {
            "name": "scores",
            "description": "スコアランキング・統計・政党別比較・CSV出力",
        },
        {
            "name": "bills",
            "description": "法案の一覧・詳細・投票結果",
        },
        {
            "name": "sessions",
            "description": "国会会期の一覧",
        },
        {
            "name": "data-quality",
            "description": "会期ごとのデータ充足状況",
        },
    ],
    license_info={"name": "MIT"},
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(CacheControlMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(members.router, prefix="/api/v1")
app.include_router(bills.router, prefix="/api/v1")
app.include_router(scores.router, prefix="/api/v1")
app.include_router(sessions.router, prefix="/api/v1")
app.include_router(data_quality.router, prefix="/api/v1")
app.include_router(reviews.router, prefix="/api/v1")
app.include_router(sleeping.router, prefix="/api/v1")


@app.get("/api/v1/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception:
        return {"status": "degraded", "database": "disconnected"}
