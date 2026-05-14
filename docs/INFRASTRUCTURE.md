# GiinScore インフラ構成

## 構成概要

| レイヤー | サービス | プラン | 月額 |
|----------|---------|--------|------|
| Frontend | Vercel | Hobby (無料) | $0 |
| Backend | Render Web Service | Starter | $7 |
| Database | Render PostgreSQL | Free (90日) | $0 |
| **合計** | | | **$7/月** |

## アーキテクチャ

```
[ユーザー] → [Vercel CDN] → Next.js (Frontend)
                                ↓ API呼び出し
                          [Render] → FastAPI (Backend)
                                        ↓
                                  [Render] → PostgreSQL 16
```

## ドメイン構成

- Frontend: `giinscore.vercel.app` (or カスタムドメイン)
- Backend: `giinscore-api.onrender.com`
- WordPress ドメインのサブドメインを CNAME で `cname.vercel-dns.com` に向ける

## IaC (Terraform)

`infra/` ディレクトリで管理:
- Provider: `vercel/vercel`, `render-oss/render`
- State: ローカル管理

```bash
cd infra
cp terraform.tfvars.example terraform.tfvars  # 認証情報を入力
terraform init
terraform plan
terraform apply
```

## 料金ダッシュボード（スマホ確認用）

| サービス | URL |
|----------|-----|
| Vercel Usage | https://vercel.com/dashboard → Usage タブ |
| Render Billing | https://dashboard.render.com → Billing |

## 注意事項

- Render Free DB は **90日制限** → 期限前に Starter ($7/月) へ移行
- Vercel Hobby は **非商用のみ** → 商用なら Pro ($20/月)
- Render Starter は常時起動（コールドスタートなし）

## スケールアップ目安

| トリガー | アクション | 追加コスト |
|----------|-----------|-----------|
| DB 90日期限 | Render PostgreSQL → Starter | +$7/月 |
| 商用利用開始 | Vercel → Pro | +$20/月 |
| レスポンス遅延 | Render → Standard | +$18/月 |
| トラフィック増大 | Vercel Pro + Render Standard + Managed DB | ~$50/月 |
