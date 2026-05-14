# GiinScore TODO

## インフラ・デプロイ

- [ ] Vercel アカウントで GitHub App をインストール
- [ ] Vercel API Token を発行 (https://vercel.com/account/tokens)
- [ ] Render API Key を発行 (https://dashboard.render.com/u/settings → API Keys)
- [ ] Render Owner ID を確認
- [ ] `infra/terraform.tfvars` に認証情報を設定
- [ ] `terraform init && terraform apply` で初回デプロイ
- [ ] Frontend アクセス確認
- [ ] Backend `/api/v1/health` ヘルスチェック確認
- [ ] フロント → バックエンド間 API 通信確認
- [ ] 初回データパイプライン実行（本番DB投入）

## ドメイン

- [ ] WordPress ドメインのサブドメイン決定
- [ ] DNS に CNAME レコード追加 (`cname.vercel-dns.com`)
- [ ] Vercel でドメイン検証完了
- [ ] `terraform.tfvars` の `frontend_domain` を更新して再 apply

## 運用

- [ ] Render Free DB の90日期限をカレンダーに登録
- [ ] GitHub Actions の `pipeline.yml` に本番 DATABASE_URL を Secret 追加
- [ ] Discord 通知 Webhook の本番設定
- [ ] Anthropic API Key の本番設定

## 将来対応

- [ ] Terraform state を Terraform Cloud に移行
- [ ] GitHub PAT の Issue 書き込み権限追加（Fine-grained token の Permissions → Issues → Read and write）
- [ ] Vercel Pro への移行判断（商用利用時）
- [ ] Render PostgreSQL の Starter 移行（90日期限前）
- [ ] モニタリング・アラート設定（Render Dashboard / Vercel Analytics）
