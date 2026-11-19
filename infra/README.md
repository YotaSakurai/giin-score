# GiinScore Infrastructure

## 推奨構成: 単一VPS（月額 ~€4.35）

DBが既に571MB（speechesテーブルが大半）あり会期ごとに成長するため、
無料枠DB（Neon 500MB / Render Free 90日）は不向き。
単一VPS（例: Hetzner CX22 2vCPU/4GB）に `docker-compose.prod.yml` を
そのままデプロイする構成が最も安価で運用が単純。

```
[ローカル(WSL2)]                     [VPS]
 パイプライン(cron) ──sync-db.sh──▶  nginx ─▶ frontend (Next.js)
 Ollama品質分析                            └▶ backend (FastAPI) ─ db (PostgreSQL)
```

- スクレイピング・LLM分析・スコアリングは従来どおりローカルで実行（Ollama依存のため）
- `scripts/sync-db.sh vps user@host` で日次結果をVPSへ反映（daily-pipeline.sh 末尾に追加可能）
- SSL: Cloudflare（無料）をVPSの前段に置くのが最も簡単（nginx側はHTTP 80のまま）

### 公開前のローカル検証（ステージング）

本番と同一のスタック（nginx + 本番ビルドfrontend + 本番モードbackend + 専用DB）を
ローカルの :8080 で起動して確認できる:

```bash
cp .env.production.example .env.production   # 初回のみ。パスワード等を編集
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
./scripts/sync-db.sh local                    # 開発DBのデータを投入
# → http://localhost:8080 で動作確認
docker compose -p giin-score-prod down        # 停止
```

開発スタック（`docker compose up`）とはプロジェクト名・ポート・ボリュームが
分離されているため同時起動できる。

### VPSデプロイ手順

```bash
# VPS側（初回）
git clone git@github.com:YotaSakurai/giin-score.git && cd giin-score
cp .env.production.example .env.production   # HTTP_PORT=80, ドメインURLに編集
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build

# ローカル側（データ反映）
./scripts/sync-db.sh vps user@your-vps-host
```

---

## 代替: Vercel + Render (Terraform)

Vercel (Frontend) + Render (Backend + PostgreSQL) の構成を Terraform で管理する。
※ Render PostgreSQL Free は90日で失効し、有料化すると合計 $14/月 になる点に注意。

## 前提条件

- [Terraform](https://developer.hashicorp.com/terraform/install) >= 1.5
- [Vercel アカウント](https://vercel.com/) + GitHub App インストール済み
- [Render アカウント](https://render.com/)

## API キーの取得

| サービス | 取得場所 |
|----------|----------|
| Vercel API Token | https://vercel.com/account/tokens |
| Render API Key | https://dashboard.render.com/u/settings → API Keys |
| Render Owner ID | Dashboard の URL (`usr-xxx`) or Team Settings (`tea-xxx`) |

## セットアップ

```bash
cd infra

# 変数ファイルを作成
cp terraform.tfvars.example terraform.tfvars
# terraform.tfvars を編集して認証情報を入力

# 初期化
terraform init

# プレビュー
terraform plan

# デプロイ
terraform apply
```

## ドメイン設定

`frontend_domain` を設定した場合、Vercel が DNS レコードを要求する。
`terraform apply` 後に Vercel Dashboard でドメイン設定を確認し、DNS プロバイダーで CNAME レコードを追加する。

```
giinscore.example.com  CNAME  cname.vercel-dns.com
```

## コスト

| リソース | プラン | 月額 |
|----------|--------|------|
| Vercel Frontend | Hobby | $0 |
| Render Web Service | Starter | $7 |
| Render PostgreSQL | Free (90日) | $0 |
| **合計** | | **$7/月** |

## リソース削除

```bash
terraform destroy
```
