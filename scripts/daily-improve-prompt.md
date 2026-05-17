# GiinScore デイリー自動改善タスク

あなたはGiinScoreプロジェクトの自動改善エージェントです。
**必ず何かしらのコード変更を行ってください。** 「改善点なし」は許容されません。

## プロジェクト構造
- `frontend/` — Next.js 16 + React 19 + TypeScript + Tailwind v4 + shadcn/ui + Recharts
- `backend/` — FastAPI + SQLAlchemy + PostgreSQL + Alembic
- テスト: `frontend` → tsc + next build / `backend` → ruff + pytest

## 今日のタスクカテゴリ

環境変数 `IMPROVE_CATEGORY` の値に基づいて実行してください:

### category=frontend_ux
以下から **2〜3つ** 実装せよ:
- `frontend/src/app/` 内のページコンポーネントで `LoadingSpinner` が使われている箇所を文脈別スケルトン (`TableSkeleton`/`CardSkeleton`/`LoadingSkeleton`) に置換
- 空状態（データ0件）のUIを改善: アイコン追加、説明テキスト追加、アクションボタン提案
- テーブルの行ホバー効果統一 (`hover:bg-muted/50 transition-colors`)
- モバイルでのテーブル表示をカードビューに切り替え (`hidden sm:block` + `sm:hidden` grid)
- フォームinputにフォーカスリング統一 (`focus-visible:ring-2 ring-ring`)

### category=backend_optimize
以下から **2〜3つ** 実装せよ:
- `backend/app/api/` のエンドポイントで N+1クエリを `joinedload`/`selectinload` で解消
- レスポンスモデルに `model_config = {"from_attributes": True}` が不足しているPydanticモデルを修正
- 新しいAPI集計エンドポイントの追加（例: `/api/v1/stats/trends`, `/api/v1/members/{id}/activity-summary`）
- `backend/app/services/scoring.py` のクエリ最適化（バルク取得、サブクエリ削減）
- パイプラインの進捗ログ改善（処理速度、ETA表示）

### category=a11y_dark
以下から **2〜3つ** 実装せよ:
- `role="img"` + `aria-label` が不足しているSVGアイコンやチャートに追加
- ハードコーディングされた色値（`#xxx`, `text-gray-600` 等）をダークモード対応のsemantic色に変更
- `<table>` に `<caption>` や `aria-describedby` を追加
- キーボード操作でフォーカスが見えない要素に `focus-visible` スタイルを追加
- カラーコントラスト不足の `text-muted-foreground/50` を `/70` 以上に修正

### category=test_quality
以下から **2〜3つ** 実装せよ:
- `backend/app/tests/` に新しいテストファイルを追加（未テストのAPIエンドポイント用）
- 既存テストにエッジケースを追加（空データ、大量データ、不正入力）
- フロントエンドの `lib/` ユーティリティ関数にユニットテストを追加
- 型安全性の強化: `any` 型を具体的な型に置換、`as` キャストの削減
- dead code（未使用のimport、関数、変数）を検出して削除

### category=micro_feature
以下から **1〜2つ** 実装せよ:
- 議員詳細ページにキーボードショートカット追加（J/K でタブ切り替え等）
- 一覧ページにスクロール位置の復元機能（`sessionStorage` 利用）
- 比較ページにURL短縮のためのハッシュベースID共有
- バックエンドに `/api/v1/health` エンドポイント追加（DB接続確認、最終パイプライン実行日時）
- トースト通知コンポーネントの追加（お気に入り追加/削除時のフィードバック）

### category=performance
以下から **2〜3つ** 実装せよ:
- 大きなリストコンポーネントに `React.memo` + `useCallback` を適用
- 画像/チャートの遅延読み込み (`loading="lazy"`, dynamic import)
- SWRの `dedupingInterval` / `revalidateOnFocus` 設定を最適化
- CSSクラスの重複削除、共通パターンの変数化
- `useMemo` が不足しているデータ変換処理に追加

### category=scoring_pipeline
以下から **2〜3つ** 実装せよ:
- スコアリングロジックの改善提案: `backend/app/services/scoring.py` の正規化手法のコメント追加
- パイプラインのエラーハンドリング強化（リトライ、部分失敗時の継続）
- 新しい分析指標の追加（例: 会期間の変化率計算、政党平均との乖離度）
- `backend/app/pipeline/analyze.py` に新しいデータ品質チェック追加
- スクレイパーのrobustness改善（タイムアウト処理、HTML構造変更への耐性）

## 実行手順

1. **CLAUDE.md を読む** — プロジェクトの方針を確認
2. **git log --oneline -10** — 直近の変更を確認（重複回避）
3. **対象ファイルを探索** — 該当カテゴリのファイルをGlob/Grepで特定
4. **実装** — 上記リストから具体的なタスクを選び実装
5. **テスト実行**:
```bash
cd frontend && npx tsc --noEmit && npx next build && cd ..
cd backend && ruff check app/ && ruff format --check app/ && python -m pytest app/tests/ -q
```
6. **サマリー出力** — `/tmp/improve-summary.md` に書き出し

## 制約
- 1ファイルあたり最大50行の変更
- 既存APIインターフェースを破壊しない
- 新しいnpm/pipパッケージを追加しない
- テストが全てパスする状態を維持
- **必ず最低1ファイルは変更すること**
