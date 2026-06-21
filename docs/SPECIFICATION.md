# GiinScore サービス仕様書

> **最終更新:** 2026-06-21
> **バージョン:** 1.0.0

---

## 1. サービス概要

GiinScore は、日本の国会議員の活動を定量的に評価・可視化するWebサービスである。
国会会議録API・衆参両院公式サイトからデータを自動収集し、5軸のスコアリングモデルで議員を評価する。

### 1.1 根本理念

- **国力の向上**と**日本国籍保持者の国民生活の向上**を最優先とする
- 政治家の評価は**立法・政策立案における実質的な能力と成果**で決まる
- スキャンダル・金銭問題・品性の問題は、能力の評価とは独立
- イデオロギー中立：「何を主張するか」ではなく「どれだけ実質的な政策議論ができているか」

---

## 2. 技術スタック

| レイヤー | 技術 |
|---------|------|
| フロントエンド | Next.js 16 (App Router) / React 19 / TypeScript |
| UIフレームワーク | Tailwind CSS v4 / shadcn/ui / Radix UI |
| チャート | Recharts 3 |
| データフェッチ | SWR 2 |
| 多言語対応 | next-intl (ja / en) |
| バックエンド | FastAPI / Python 3.12 |
| ORM | SQLAlchemy 2 |
| DB | PostgreSQL (本番) / SQLite (テスト) |
| マイグレーション | Alembic |
| LLM | Ollama (ローカル) / Anthropic Claude API |
| コンテナ | Docker Compose |
| CI/CD | GitHub Actions |
| テスト | pytest (581テスト, カバレッジ99%) / Vitest |

---

## 3. スコアリングモデル

### 3.1 5軸評価

| 軸 | 重み | 概要 |
|----|------|------|
| 立法活動 (Legislative Activity) | 25% | 法案発議・委員会質疑・質問主意書 |
| 投票行動 (Voting Behavior) | 20% | 本会議投票への参加率 |
| 政策影響力 (Policy Influence) | 20% | 成立法案数・答弁付き質問主意書 |
| 透明性 (Transparency) | 15% | 委員会出席の多様性 |
| 質問品質 (Question Quality) | 20% | LLMによる発言品質分析 |

### 3.2 各軸の算出方法

#### 立法活動スコア
- 法案主発議: ×1.0 / 共同発議(5人以下): ×0.5 / 共同発議(6-20人): ×0.3 / 共同発議(20人超): ×0.1
- 委員会質疑: 発言回数 × 発言密度係数 (平均文字数 / 3000字, 上限2.0)
- 質問主意書: 件数 × 0.5

#### 投票行動スコア
- (棄権+投票) / 投票機会 × 100
- 欠席は投票機会としてカウントされるが参加としてはカウントされない

#### 政策影響力スコア
- 成立法案: 閣法 ×1.0 / 衆法・参法 ×0.8
- 改正法案: 軽微 ×0.3 / 大規模 ×0.7
- 答弁付き質問主意書: 件数 × 0.3

#### 透明性スコア
- 発言した会議種別数 / 全会議種別数 × 100

#### 質問品質スコア
LLMが4観点で発言を分析し、平均値を算出:
- **政策関連性**: 法律・予算・制度改善に直結するか
- **建設性**: 具体的な改善提案・対案を伴うか
- **専門性**: 独自調査・データ分析に基づくか
- **国益適合性**: 国民生活向上・国力強化に直結するか

### 3.3 正規化

- 比較群: **院 × 役職カテゴリ**のグループ内でパーセンタイルランク正規化 (0〜100)
- 同点にはランクの平均値を適用
- グループ内1人のみの場合: 50.0

### 3.4 グレード

| スコア | グレード |
|--------|---------|
| 80〜100 | A |
| 60〜79 | B |
| 40〜59 | C |
| 20〜39 | D |
| 0〜19 | F |

### 3.5 重みバージョン管理

- `weight_versions` テーブルで重みの変更を履歴管理
- `is_active = True` の最新バージョンが適用される
- 変更理由を `reason` フィールドに記録

---

## 4. データパイプライン

### 4.1 パイプライン一覧

実行順序に沿って記載。`--pipeline all` で全パイプラインを順次実行する。

| # | パイプライン | データソース | 出力テーブル |
|---|------------|------------|------------|
| 1 | `members` | 衆参議員一覧ページ | members |
| 2 | `bills` | 衆議院 法案一覧ページ | bills, bill_sponsors |
| 3 | `speeches` | 国会会議録API | speeches, members |
| 4 | `votes` | 参議院 投票結果ページ | vote_results, vote_records |
| 5 | `shugiin` | 衆議院 法案詳細ページ | bills, bill_sponsors |
| 6 | `smartnews` | SmartNews SMRI CSV | bills, diet_sessions |
| 7 | `profiles` | 衆参議員一覧 (プロフィール) | members (選挙区・読み仮名) |
| 8 | `speech_quality` | Ollama / Anthropic API | speech_quality_scores |
| 9 | `scoring` | 内部計算 | member_scores, score_audit_logs |
| 10 | `analyze` | 内部計算 | Discord通知 |

### 4.2 実行方法

```bash
# Docker内で実行
docker compose exec backend python -m app.pipeline.runner --pipeline all --session 215

# 個別パイプライン
docker compose exec backend python -m app.pipeline.runner --pipeline speeches --session 215
```

### 4.3 LLM 発言品質分析

- **対象**: cabinet / chair 以外の議員の発言 (200字以上)
- **除外**: 議事進行発言 (「ただいまから〜」等)
- **バックエンド**: Ollama (デフォルト, ローカル実行) / Anthropic Claude API
- **リトライ**: 最大3回 (指数バックオフ)
- **品質ゲート**: 失敗率が閾値を超えるとパイプラインを安全停止
- **Discord通知**: 進捗・警告・停止時にwebhook送信

### 4.4 バイアス検出

スコアリング後に自動実行。以下を検出してDiscordに通知:

- **政党間バイアス**: 政党間のスコア差が閾値以上
- **院別バイアス**: 衆参間のスコア差が閾値以上
- **グレード分布異常**: 特定グレードが60%以上を占める
- **大幅スコア変動**: 前会期比で30点以上の変動

### 4.5 監査ログ

`score_audit_logs` テーブルに全スコア変更を記録:
- 前会期スコア (5軸 + 総合 + グレード)
- 当会期スコア (5軸 + 総合 + グレード)
- 差分 (diff_total)
- 使用した重みバージョン

---

## 5. データベースモデル

### 5.1 ER図 (主要テーブル)

```
members ──< member_scores >── diet_sessions
   │                              │
   ├──< speeches                  │
   │      └──< speech_quality_scores
   │
   ├──< vote_records >── vote_results >── bills
   │
   ├──< bill_sponsors >── bills
   │
   ├──< written_questions
   │
   └──< user_reviews ──< review_likes
```

### 5.2 テーブル一覧

| テーブル | 概要 | 主要カラム |
|---------|------|----------|
| members | 議員マスタ | name, chamber, party, district, role_category |
| diet_sessions | 国会会期 | session_number, kind, start_date, end_date |
| member_scores | 議員スコア (会期別) | member_id, session_id, 5軸(raw+normalized), total, grade |
| bills | 法案 | session_id, bill_kind, title, status, result |
| bill_sponsors | 法案提出者 | bill_id, member_id, sponsor_type |
| speeches | 国会発言 | session_id, member_id, meeting_name, speech_text, speech_chars |
| speech_quality_scores | 発言品質 (LLM分析) | speech_id, 4観点スコア, overall_quality, analysis_summary |
| vote_results | 投票結果 | bill_id, chamber, ayes, nays, result |
| vote_records | 個別投票記録 | vote_result_id, member_id, vote (aye/nay/abstain/absent) |
| written_questions | 質問主意書 | session_id, member_id, chamber, title, has_answer |
| user_reviews | ユーザーレビュー | member_id, reviewer_id, 5軸スコア, comment |
| review_likes | レビューいいね | review_id, liker_id |
| score_audit_logs | スコア監査ログ | member_id, prev/new 5軸+total+grade, diff_total |
| weight_versions | 重みバージョン | version, 5軸重み, is_active |
| pipeline_runs | パイプライン実行ログ | pipeline_name, status, records_processed |

---

## 6. API仕様

### 6.1 ベースURL

```
http://localhost:8000/api/v1
```

### 6.2 エンドポイント一覧

#### 議員

| メソッド | パス | 概要 | 主要パラメータ |
|---------|------|------|-------------|
| GET | `/members` | 議員一覧 (ページネーション) | chamber, party, role_category, search, district, grade, score_min/max, 各軸min/max, sort_by, sort_order, page, per_page |
| GET | `/members/scatter` | 散布図用データ | 同上 (ページネーションなし) |
| GET | `/members/districts` | 選挙区一覧 | chamber |
| GET | `/members/role-categories` | 役職カテゴリ一覧 | chamber |
| GET | `/members/{id}` | 議員詳細 | - |
| GET | `/members/{id}/scores` | スコア履歴 (全会期) | - |
| GET | `/members/{id}/similar` | 類似議員 | limit |
| GET | `/members/{id}/speeches` | 発言一覧 | page, per_page |
| GET | `/members/{id}/votes` | 投票記録 | page, per_page |
| GET | `/members/{id}/vote-pattern` | 投票パターン分析 | - |
| GET | `/members/{id}/speech-quality` | 発言品質分析 | page, per_page |
| GET | `/members/{id}/written-questions` | 質問主意書 | page, per_page |

#### スコア・ランキング

| メソッド | パス | 概要 | 主要パラメータ |
|---------|------|------|-------------|
| GET | `/scores/ranking` | ランキング | chamber, party, role_category, session_number, sort_by, limit, offset |
| GET | `/scores/stats` | 統計情報 | chamber, session_number |
| GET | `/scores/by-party` | 政党別統計 | chamber, session_number |
| GET | `/scores/party-trend` | 政党別推移 | chamber |
| GET | `/scores/movers` | スコア変動TOP | chamber, limit |
| GET | `/scores/export/csv` | CSVエクスポート | chamber, party, session_number |
| GET | `/scores/parties` | 政党一覧 | chamber |

#### 法案

| メソッド | パス | 概要 | 主要パラメータ |
|---------|------|------|-------------|
| GET | `/bills` | 法案一覧 | session_number, bill_kind, status, search, page, per_page |
| GET | `/bills/{id}` | 法案詳細 | - |

#### レビュー

| メソッド | パス | 概要 | レート制限 |
|---------|------|------|----------|
| GET | `/members/{id}/reviews` | レビュー一覧 | 60/分 |
| GET | `/members/{id}/review-summary` | レビュー集計 | 60/分 |
| POST | `/members/{id}/reviews` | レビュー投稿 | 10/分 |
| PUT | `/reviews/{id}` | レビュー更新 | 10/分 |
| DELETE | `/reviews/{id}` | レビュー削除 | 10/分 |
| POST | `/reviews/{id}/like` | いいね切替 | 30/分 |

#### その他

| メソッド | パス | 概要 |
|---------|------|------|
| GET | `/sessions` | 会期一覧 |
| GET | `/data-quality` | データ品質 |
| GET | `/data-quality/last-updated` | 最終更新日時 |
| GET | `/health` | ヘルスチェック |

### 6.3 キャッシュ制御

| パスパターン | Cache-Control |
|------------|---------------|
| `/scores/by-party` | max-age=3600 |
| `/scores/ranking` | max-age=1800 |
| `/members/{id}` | max-age=600 |
| その他API | max-age=300 |
| `/health`, `/export` | キャッシュなし |

---

## 7. フロントエンド

### 7.1 ページ構成

| パス | ページ名 | 概要 |
|------|---------|------|
| `/` | ホーム | ランキングTOP表示・統計概要・スコア変動・オンボーディング |
| `/members` | 議員一覧 | フィルタ・ソート・3ビューモード (グリッド/テーブル/散布図) |
| `/members/[id]` | 議員詳細 | レーダーチャート・時系列・発言/投票/品質分析/レビュー (タブ) |
| `/compare` | 議員比較 | 最大4名を5軸レーダーチャートで比較 |
| `/parties` | 政党別統計 | 政党別平均スコア・グレード分布・トレンド |
| `/quality-ranking` | 質問品質ランキング | LLM分析スコアによるランキング |
| `/bills` | 法案一覧 | 検索・フィルタ (種別/状態/会期) |
| `/bills/[id]` | 法案詳細 | 提出者・投票結果 |
| `/favorites` | お気に入り | localStorage保存の議員一覧 |
| `/about` | スコア算出方法 | 各軸の説明・グレード基準 |
| `/data-quality` | データ品質 | 会期別データ収集状況 |
| `/api-docs` | APIドキュメント | 開発者向けAPI仕様 |

### 7.2 主要機能

#### フィルタリング
- **基本フィルタ**: 院・政党・役職カテゴリ・選挙区・テキスト検索
- **スコアフィルタ**: グレード複数選択・総合スコア範囲・各軸スコア範囲
- **プリセット**: 高評価議員・質問力上位・立法活動活発・低評価
- **プリセット保存**: ユーザー定義フィルタをlocalStorageに保存 (最大5個)

#### ビューモード
- **グリッド**: カード形式 (デフォルト、レスポンシブ)
- **テーブル**: データテーブル (ヘッダークリックでソート)
- **散布図**: 任意の2軸で散布図プロット

#### 議員比較
- 議員一覧・ホームからチェックボックスで選択 (最大4名)
- 5軸レーダーチャートでオーバーレイ比較
- 各軸バーチャートで横並び比較

#### ユーザーレビュー
- 5軸評価 (0〜100のスライダー) + コメント
- いいね機能 (トグル)
- ソート: いいね順 / 新着順
- reviewer_id による編集・削除制御 (ユーザー認証なし)

#### お気に入り
- localStorage で管理 (サーバーレス)
- お気に入り議員の一覧表示

#### ダークモード
- next-themes によるシステム連動 / 手動切替
- 全コンポーネントがダークモード対応

#### 多言語対応
- 日本語 (デフォルト) / 英語
- URLプレフィックス: `/ja/...`, `/en/...`

#### SEO
- 動的メタデータ (title, description, OGP)
- OGP画像の動的生成 (議員詳細)
- JSON-LD構造化データ
- 動的sitemap.xml / robots.txt

### 7.3 レスポンシブ対応

| ブレークポイント | デバイス | レイアウト |
|---------------|---------|----------|
| < 640px | モバイル | 1カラム・ハンバーガーメニュー (Sheet) |
| 640〜1024px | タブレット | 2カラムグリッド |
| > 1024px | デスクトップ | 3〜4カラムグリッド |

---

## 8. インフラ構成

### 8.1 Docker Compose

| サービス | イメージ | ポート |
|---------|---------|-------|
| db | PostgreSQL 16 | 5432 |
| backend | Python 3.12 + FastAPI | 8000 |
| frontend | Node.js + Next.js (ローカル開発) | 3000 |

### 8.2 CI/CD (GitHub Actions)

| ワークフロー | トリガー | 内容 |
|------------|---------|------|
| CI | push / PR | ruff check, ruff format, pytest, eslint, tsc, build, test |
| Pipeline | 週次 (cron) | 全パイプライン実行 |

---

## 9. テスト

| 項目 | 値 |
|------|-----|
| テスト数 | 581 passed, 1 skipped |
| カバレッジ | 99% (7,699行中56行未カバー) |
| テストフレームワーク | pytest (backend) / Vitest (frontend) |
| テストDB | SQLite (インメモリ相当) |
| モック | unittest.mock (httpx, LLM, Discord webhook) |

---

## 10. 現在のUI/UXの状況

### 10.1 実装済みのUI要素

- shadcn/ui ベースの統一的なデザインシステム
- ダークモード完全対応
- レスポンシブ対応 (モバイル〜デスクトップ)
- スケルトンローディング
- エラーバウンダリ
- オンボーディング (初回訪問ガイド)
- フローティング比較ボタン
- アクティブフィルタのバッジ表示

### 10.2 UI/UX改善の余地がある領域

#### ナビゲーション・情報設計
- ページ間の遷移フローが直線的で、ユーザーの探索的な利用を十分にサポートできていない
- 議員詳細ページのタブが6つあり、情報過多になりやすい
- モバイルでのフィルタ操作が煩雑

#### ビジュアル・インタラクション
- チャートの操作性 (ズーム・ドリルダウン)
- 散布図のインタラクション (ホバー詳細、クリック遷移)
- スコア変動のアニメーション表現
- グレードバッジの視覚的インパクト

#### アクセシビリティ
- キーボードナビゲーションの一貫性
- スクリーンリーダー対応の強化
- 色覚多様性への対応 (グレードカラーの代替表現)

#### パフォーマンス体感
- 初回表示の体感速度
- ページ遷移のスムーズさ
- 大量データ時のスクロール性能
