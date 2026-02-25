# GiinScore - 政治家活動スコアリングダッシュボード

国会の公開データを基に政治家の活動を4軸（立法活動・投票行動・政策影響力・透明性）でスコア化・可視化するWebアプリ。

## 技術スタック

- **Frontend**: Next.js 16 (App Router) + React 19 + TypeScript + Tailwind CSS v4 + shadcn/ui + Recharts + SWR
- **Backend**: Python (FastAPI) + SQLAlchemy + Alembic
- **DB**: PostgreSQL 16
- **コンテナ**: Docker Compose
- **CI**: GitHub Actions（ruff lint/format, pytest, ESLint, tsc, Vitest）

## セットアップ

### 前提条件

- Docker & Docker Compose
- Node.js 20+
- Python 3.11+

### 1. クローン & 環境変数

```bash
git clone git@github.com:YotaSakurai/giin-score.git
cd giin-score
cp .env.example .env
```

### 2. バックエンド起動（Docker）

```bash
docker compose up -d db backend
```

PostgreSQL (port 5433) と FastAPI (port 8000) が起動します。DBマイグレーションは起動時に自動実行されます。

### 3. フロントエンド起動

```bash
cd frontend
npm install
npm run dev
```

http://localhost:3000 でダッシュボードが開きます。

## ページ構成

| URL | 内容 |
|-----|------|
| `/` | ランキングTOP100 + 概要統計（5指標）+ 院フィルタ |
| `/members` | 議員カード一覧（検索・フィルタ・ソート） |
| `/members/[id]` | 議員詳細: レーダーチャート + スコア内訳 + 重みスライダー |
| `/bills` | 法案一覧（種別・状態フィルタ） |
| `/bills/[id]` | 法案詳細 + 賛否グラフ |
| `/about` | スコア算出方法・データソース・限界 |

## API エンドポイント

バックエンド起動後、http://localhost:8000/docs でSwagger UIを確認できます。

```
GET /api/v1/health                  ヘルスチェック（DB接続確認含む）

GET /api/v1/members                 議員一覧（検索・フィルタ・ソート・ページネーション）
GET /api/v1/members/{id}            議員詳細
GET /api/v1/members/{id}/scores     スコア履歴
GET /api/v1/members/{id}/speeches   発言一覧（ページネーション）
GET /api/v1/members/{id}/votes      投票記録（ページネーション）

GET /api/v1/bills                   法案一覧（種別・状態フィルタ・ページネーション）
GET /api/v1/bills/{id}              法案詳細（発議者・投票結果含む）

GET /api/v1/scores/ranking          ランキング（院・政党・会期フィルタ）
GET /api/v1/scores/stats            統計情報（平均・中央値・グレード分布）

GET /api/v1/sessions                会期一覧
```

## データ取得パイプライン

国会データを取得してスコアを算出するCLIパイプライン:

```bash
# 全パイプライン一括実行（第213回国会）
docker compose exec backend python -m app.pipeline.runner --pipeline all --session 213

# 個別実行
docker compose exec backend python -m app.pipeline.runner --pipeline bills --session 213
docker compose exec backend python -m app.pipeline.runner --pipeline speeches --session 213
docker compose exec backend python -m app.pipeline.runner --pipeline votes --session 213
docker compose exec backend python -m app.pipeline.runner --pipeline shugiin --session 213
docker compose exec backend python -m app.pipeline.runner --pipeline scoring --session 213
docker compose exec backend python -m app.pipeline.runner --pipeline smartnews --session 213
```

### データソース

| パイプライン | データソース | 取得内容 |
|------------|------------|---------|
| speeches | [国会会議録API](https://kokkai.ndl.go.jp/api.html) | 発言記録・議員情報 |
| bills | [衆議院サイト](https://www.shugiin.go.jp/) | 法案一覧 |
| shugiin | [衆議院サイト](https://www.shugiin.go.jp/) | 法案詳細 |
| votes | [参議院サイト](https://www.sangiin.go.jp/) | 投票記録 |
| smartnews | CSVファイル | SmartNews法案データ |

## テスト

```bash
# バックエンド
docker compose exec backend pytest -v

# フロントエンド
cd frontend && npm run test:ci
```

## スコアリング概要

| 軸 | 重み | 計測内容 |
|----|------|----------|
| 立法活動 (LAS) | 30% | 法案発議（発議者タイプ・共同発議者数で重み付け）+ 委員会質疑（回数 × 発言密度） |
| 投票行動 (VBS) | 25% | 投票参加率（棄権は参加扱い、欠席は非参加） |
| 政策影響力 (PIS) | 25% | 成立法案（法案種別×改正規模で重み付け: 閣法1.0 / 衆法・参法0.8） |
| 透明性 (TS) | 20% | 多様な委員会への参加率（発言ユニーク会議数 / 全会議数） |

- **正規化**: パーセンタイルランク方式（0-100）、同点は平均ランク方式
- **比較群**: 同一会期 × 同一院 × 同一role_category
- **グレード**: A(80-100) / B(60-79) / C(40-59) / D(20-39) / F(0-19)
- **カスタマイズ**: 重みはユーザーがスライダーで変更可能

## ライセンス

本プロジェクトのスコアは政治家の活動量の可視化であり、政治家の能力や資質の評価ではありません。
