# GiinScore - 政治家活動スコアリングダッシュボード

国会の公開データを基に政治家の活動を4軸（立法活動・投票行動・政策影響力・透明性）でスコア化・可視化するWebアプリ。

## 技術スタック

- **Frontend**: Next.js 15 (App Router) + TypeScript + Tailwind CSS + shadcn/ui + Recharts
- **Backend**: Python (FastAPI) + SQLAlchemy + Alembic
- **DB**: PostgreSQL
- **コンテナ**: Docker Compose

## セットアップ

### 前提条件

- Docker & Docker Compose
- Node.js 18+
- Python 3.11+

### 1. クローン & 環境変数

```bash
git clone git@github.com:YotaSakurai/giin-score.git
cd giin-score
cp .env.example .env
```

### 2. バックエンド起動（Docker）

```bash
docker compose up -d
```

PostgreSQL (port 5432) と FastAPI (port 8000) が起動します。

### 3. DBマイグレーション

```bash
docker compose exec backend alembic upgrade head
```

### 4. フロントエンド起動

```bash
cd frontend
npm install
npm run dev
```

http://localhost:3000 でダッシュボードが開きます。

### フロントエンドだけ試す場合（Docker不要）

バックエンドなしでもモックデータでUIを確認できます。

```bash
cd frontend
npm install
npm run dev
```

## ページ構成

| URL | 内容 |
|-----|------|
| `/` | ランキングTOP20 + 概要統計 + 院フィルタ |
| `/members` | 議員カード一覧（検索・フィルタ・ソート） |
| `/members/[id]` | 議員詳細: レーダーチャート + スコア内訳 + 重みスライダー |
| `/bills` | 法案一覧（種別・状態フィルタ） |
| `/bills/[id]` | 法案詳細 + 賛否グラフ |
| `/about` | スコア算出方法・データソース・限界 |

## API エンドポイント

バックエンド起動後、http://localhost:8000/docs でSwagger UIを確認できます。

```
GET /api/v1/health                  ヘルスチェック
GET /api/v1/members                 議員一覧
GET /api/v1/members/{id}            議員詳細
GET /api/v1/members/{id}/scores     スコア詳細
GET /api/v1/members/{id}/speeches   発言一覧
GET /api/v1/members/{id}/votes      投票記録
GET /api/v1/bills                   法案一覧
GET /api/v1/bills/{id}              法案詳細
GET /api/v1/scores/ranking          ランキング
GET /api/v1/scores/stats            統計情報
GET /api/v1/sessions                会期一覧
```

## データ取得パイプライン

実際の国会データを取得してスコアを算出する場合:

```bash
# 全パイプライン一括実行（第213回国会）
docker compose exec backend python -m app.pipeline.runner --pipeline all --session 213

# 個別実行
docker compose exec backend python -m app.pipeline.runner --pipeline bills
docker compose exec backend python -m app.pipeline.runner --pipeline members --session 213
docker compose exec backend python -m app.pipeline.runner --pipeline speeches --session 213
docker compose exec backend python -m app.pipeline.runner --pipeline votes --session 213
docker compose exec backend python -m app.pipeline.runner --pipeline scoring --session 213
```

## テスト

```bash
docker compose exec backend pytest
```

## スコアリング概要

| 軸 | 重み | 計測内容 |
|----|------|----------|
| 立法活動 | 30% | 法案発議数・委員会質疑回数 |
| 投票行動 | 25% | 投票参加率 |
| 政策影響力 | 25% | 成立法案数 |
| 透明性 | 20% | 委員会発言頻度 |

- パーセンタイルランク方式（0-100）で正規化
- 比較群: 同一会期 × 同一院 × 同一role_category
- グレード: A(80-100) / B(60-79) / C(40-59) / D(20-39) / F(0-19)
- 重みはユーザーがスライダーで変更可能
