# GiinScore Infrastructure (Terraform)

Vercel (Frontend) + Render (Backend + PostgreSQL) の構成を Terraform で管理する。

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
