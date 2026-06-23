"use client";

import { useState } from "react";
import Image from "next/image";
import { Link } from "@/i18n/navigation";
import { Card, CardContent } from "@/components/ui/card";
import {
  Trophy, Users, UserRoundSearch, Building2, GitCompareArrows,
  MessageSquareText, Star, FileText, FileSearch, BookOpen,
  Monitor, Moon, ChevronRight,
} from "lucide-react";

/* ------------------------------------------------------------------ */
/* 目次データ                                                          */
/* ------------------------------------------------------------------ */
const TOC = [
  { id: "ranking",         label: "ランキング（ホーム）", icon: Trophy },
  { id: "members",         label: "議員一覧",           icon: Users },
  { id: "member-detail",   label: "議員詳細",           icon: UserRoundSearch },
  { id: "parties",         label: "政党別統計",          icon: Building2 },
  { id: "compare",         label: "議員比較",           icon: GitCompareArrows },
  { id: "quality",         label: "質問品質ランキング",   icon: MessageSquareText },
  { id: "favorites",       label: "お気に入り",          icon: Star },
  { id: "bills",           label: "法案一覧",           icon: FileText },
  { id: "bill-detail",     label: "法案詳細",           icon: FileSearch },
  { id: "about",           label: "スコアについて",       icon: BookOpen },
  { id: "mobile",          label: "モバイル対応",         icon: Monitor },
  { id: "dark",            label: "ダークモード",         icon: Moon },
] as const;

/* ------------------------------------------------------------------ */
/* 共通: 画像 + キャプション                                             */
/* ------------------------------------------------------------------ */
function Screenshot({ src, alt, caption }: { src: string; alt: string; caption?: string }) {
  return (
    <figure className="my-6">
      <div className="overflow-hidden rounded-xl border shadow-sm">
        <Image
          src={src}
          alt={alt}
          width={1440}
          height={900}
          className="w-full h-auto"
          quality={85}
        />
      </div>
      {caption && (
        <figcaption className="mt-2 text-center text-xs text-muted-foreground">{caption}</figcaption>
      )}
    </figure>
  );
}

function SectionHeading({ id, label, icon: Icon }: { id: string; label: string; icon: React.ComponentType<{ className?: string }> }) {
  return (
    <h2 id={id} className="flex items-center gap-2.5 text-xl font-bold text-foreground mt-14 mb-4 scroll-mt-20">
      <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-100 dark:bg-blue-950/50 text-blue-600 dark:text-blue-400">
        <Icon className="h-4 w-4" />
      </div>
      {label}
    </h2>
  );
}

function Tip({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex gap-3 rounded-lg bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800 px-4 py-3 my-4">
      <span className="text-blue-600 dark:text-blue-400 text-sm font-bold shrink-0">Tip</span>
      <p className="text-sm text-blue-800 dark:text-blue-200">{children}</p>
    </div>
  );
}

function FeatureList({ items }: { items: { title: string; desc: string }[] }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 my-4">
      {items.map((item) => (
        <div key={item.title} className="rounded-lg border px-4 py-3">
          <p className="text-sm font-medium text-foreground">{item.title}</p>
          <p className="text-xs text-muted-foreground mt-0.5">{item.desc}</p>
        </div>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* メインコンポーネント                                                  */
/* ------------------------------------------------------------------ */
export function GuideContent() {
  const [tocOpen, setTocOpen] = useState(false);

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      {/* ヘッダー */}
      <h1 className="text-2xl sm:text-3xl font-bold text-foreground mb-2">使い方ガイド</h1>
      <p className="text-sm text-muted-foreground mb-8">
        GiinScoreの各画面の機能と操作方法を、スクリーンショット付きで解説します。
      </p>

      {/* 目次 (モバイル折りたたみ) */}
      <Card className="mb-10">
        <CardContent className="p-4">
          <button
            type="button"
            className="flex w-full items-center justify-between sm:cursor-default"
            onClick={() => setTocOpen(!tocOpen)}
          >
            <p className="text-sm font-semibold text-foreground">目次</p>
            <ChevronRight className={`h-4 w-4 text-muted-foreground sm:hidden transition-transform ${tocOpen ? "rotate-90" : ""}`} />
          </button>
          <nav className={`mt-3 ${tocOpen ? "" : "hidden sm:block"}`} aria-label="ガイド目次">
            <ol className="grid gap-1 sm:grid-cols-2 lg:grid-cols-3">
              {TOC.map((item, i) => {
                const Icon = item.icon;
                return (
                  <li key={item.id}>
                    <a
                      href={`#${item.id}`}
                      className="flex items-center gap-2 rounded-md px-2.5 py-1.5 text-sm text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors"
                    >
                      <Icon className="h-3.5 w-3.5 shrink-0" />
                      <span>{i + 1}. {item.label}</span>
                    </a>
                  </li>
                );
              })}
            </ol>
          </nav>
        </CardContent>
      </Card>

      {/* ===== 共通 UI ===== */}
      <div className="rounded-lg bg-muted/30 border px-4 py-3 mb-10">
        <p className="text-sm font-medium text-foreground mb-2">共通操作</p>
        <ul className="text-sm text-muted-foreground space-y-1.5">
          <li><kbd className="rounded border bg-background px-1.5 py-0.5 text-xs font-mono">/</kbd> キーで検索ボックスにフォーカス</li>
          <li>画面上部の<span className="text-blue-600 dark:text-blue-400 font-medium">青いプログレスバー</span>で読了位置を確認</li>
          <li>長いページでは画面左下の<span className="font-medium">↑ボタン</span>でページトップへ戻れます</li>
          <li>ヘッダー右上の<span className="font-medium">月/太陽アイコン</span>でダークモードを切り替え</li>
        </ul>
      </div>

      {/* ===== 1. ランキング ===== */}
      <SectionHeading id="ranking" label="ランキング（ホーム）" icon={Trophy} />
      <p className="text-sm text-muted-foreground mb-2">
        トップページでは議員の活動スコアランキングを表示します。初回訪問時には3ステップの使い方ガイドが表示されます。
      </p>
      <Screenshot src="/guide/home-desktop.png" alt="ランキング画面" caption="ランキング画面 — 統計カード・選挙区検索・ランキングテーブル" />

      <h3 className="text-base font-semibold mt-6 mb-2">統計サマリー</h3>
      <p className="text-sm text-muted-foreground">
        画面中央の5つのカードには対象議員数・平均スコア・中央値・最高スコア・最低スコアが表示されます。
        ページ表示時に数値がカウントアップアニメーションで動きます。
      </p>

      <Screenshot src="/guide/home-desktop-stats.png" alt="統計カードとランキング" caption="統計サマリーとTOP3ハイライト" />

      <h3 className="text-base font-semibold mt-6 mb-2">主な操作</h3>
      <FeatureList items={[
        { title: "会期切り替え", desc: "プルダウンで過去の国会会期を選択できます" },
        { title: "院・政党フィルタ", desc: "衆議院/参議院、特定の政党で絞り込み" },
        { title: "ソート項目", desc: "総合・立法・投票・影響・透明・質問の各軸で並び替え" },
        { title: "選挙区検索", desc: "選挙区名を入力して地元議員を検索" },
      ]} />

      <Tip>降順表示時は上位3名が金・銀・銅メダル付きカードで強調されます。</Tip>

      {/* ===== 2. 議員一覧 ===== */}
      <SectionHeading id="members" label="議員一覧" icon={Users} />
      <p className="text-sm text-muted-foreground mb-2">
        全議員を検索・フィルタして閲覧するページです。3つの表示モードを切り替えられます。
      </p>

      <h3 className="text-base font-semibold mt-6 mb-2">カードビュー</h3>
      <Screenshot src="/guide/members-desktop.png" alt="議員一覧 カードビュー" caption="カードビュー — グレードバッジ・5軸スコアバー・議員タイプ" />
      <p className="text-sm text-muted-foreground">
        各議員がカード形式で表示されます。グレードバッジにマウスを乗せると拡大、カード全体にホバーすると浮き上がるエフェクトがかかります。
      </p>

      <h3 className="text-base font-semibold mt-6 mb-2">テーブルビュー</h3>
      <Screenshot src="/guide/members-table.png" alt="議員一覧 テーブルビュー" caption="テーブルビュー — 列ヘッダークリックでソート可能" />

      <h3 className="text-base font-semibold mt-6 mb-2">散布図ビュー</h3>
      <Screenshot src="/guide/members-scatter.png" alt="議員一覧 散布図ビュー" caption="散布図ビュー — X軸・Y軸・色分けを自由に変更" />
      <p className="text-sm text-muted-foreground">
        任意の2軸（立法活動・投票行動・政策影響力・透明性・質問品質）を選んで議員をプロットできます。
        回帰直線と相関係数（R値）が自動表示されます。
      </p>

      <h3 className="text-base font-semibold mt-6 mb-2">フィルタ機能</h3>
      <FeatureList items={[
        { title: "議員名検索", desc: "名前の一部を入力するとサジェストが表示される" },
        { title: "院・政党・役職", desc: "プルダウンで絞り込み。選挙区も部分一致で検索" },
        { title: "クイック絞り込み", desc: "「低活動議員(F)」「高活動議員(A)」等のワンクリックフィルタ" },
        { title: "プリセット", desc: "高評価議員・質問力上位・立法活動活発・低評価議員" },
        { title: "詳細フィルタ", desc: "グレード複数選択・5軸ごとのスコアレンジ指定" },
      ]} />

      <Tip>フィルタバーはスクロール中も画面上部に固定されるので、いつでも操作できます。</Tip>

      {/* ===== 3. 議員詳細 ===== */}
      <SectionHeading id="member-detail" label="議員詳細" icon={UserRoundSearch} />
      <p className="text-sm text-muted-foreground mb-2">
        個別の議員の活動データを詳しく見るページです。パンくずリストで「ホーム → 議員一覧 → 議員名」と現在位置を確認できます。
      </p>
      <Screenshot src="/guide/member-detail-desktop.png" alt="議員詳細" caption="議員詳細 — プロフィール・レーダーチャート・特徴サマリー" />

      <h3 className="text-base font-semibold mt-6 mb-2">ヘッダー情報</h3>
      <FeatureList items={[
        { title: "プロフィール", desc: "名前・読み仮名・院・政党・選挙区・党内順位" },
        { title: "グレードバッジ", desc: "右上に大きくグレードとスコアを表示。前会期比も" },
        { title: "☆ お気に入り", desc: "クリックでお気に入りに追加・解除" },
        { title: "シェアボタン", desc: "X・LINE・Facebook・クリップボードへ共有" },
      ]} />

      <h3 className="text-base font-semibold mt-6 mb-2">スコア分析</h3>
      <Screenshot src="/guide/member-detail-scores.png" alt="スコア分析" caption="全体平均との比較バー・重みカスタマイズスライダー" />
      <p className="text-sm text-muted-foreground">
        レーダーチャート・全体平均との比較バー（赤=平均以下、緑=平均以上）に加えて、
        <strong>重みカスタマイズ</strong>機能でスライダーを調整し、自分の価値観で総合スコアを再計算できます。
        「立法重視」「質問品質重視」などのプリセットも用意しています。
      </p>

      <h3 className="text-base font-semibold mt-6 mb-2">タブ</h3>
      <FeatureList items={[
        { title: "発言記録", desc: "国会での発言一覧。委員会名・日付・発言内容を表示" },
        { title: "投票記録", desc: "各法案への賛成/反対/欠席。投票パターン分析付き" },
        { title: "質問品質", desc: "AI分析による発言品質。政策関連性・建設性・専門性・国益" },
        { title: "質問主意書", desc: "提出した質問主意書の一覧。答弁書リンク付き" },
        { title: "スコア履歴", desc: "会期ごとのスコア推移折れ線グラフ" },
        { title: "レビュー", desc: "ユーザーによる5軸評価とコメント。いいね機能付き" },
      ]} />

      {/* ===== 4. 政党別統計 ===== */}
      <SectionHeading id="parties" label="政党別統計" icon={Building2} />
      <p className="text-sm text-muted-foreground mb-2">
        政党ごとの議員活動スコアを集計・比較するページです。
      </p>
      <Screenshot src="/guide/parties-desktop.png" alt="政党別統計" caption="政党別の平均スコア比較グラフ" />
      <FeatureList items={[
        { title: "平均スコア比較", desc: "横棒グラフで全政党の平均スコアを降順表示" },
        { title: "グレード分布", desc: "政党ごとのA〜Fの構成比率を積み上げ棒グラフで表示" },
        { title: "5軸平均比較", desc: "各政党の5軸スコア平均をテーブルで並列比較" },
        { title: "トレンド", desc: "会期ごとの政党別スコア推移の折れ線グラフ" },
      ]} />

      {/* ===== 5. 議員比較 ===== */}
      <SectionHeading id="compare" label="議員比較" icon={GitCompareArrows} />
      <p className="text-sm text-muted-foreground mb-2">
        最大4名の議員を選んでスコアを並列比較できます。
      </p>
      <Screenshot src="/guide/compare-desktop.png" alt="議員比較" caption="議員比較 — 検索またはテンプレートから議員を追加" />
      <FeatureList items={[
        { title: "検索で追加", desc: "議員名を入力してサジェストから選択" },
        { title: "テンプレート", desc: "Aグレード議員・質問品質TOP・お気に入りから一括追加" },
        { title: "レーダーチャート", desc: "選択した議員のスコアを重ね合わせ表示" },
        { title: "スコアバー", desc: "各軸のスコアを横棒で並列比較" },
      ]} />
      <Tip>比較対象はlocalStorageに保存されるため、ブラウザを閉じても維持されます。</Tip>

      {/* ===== 6. 質問品質ランキング ===== */}
      <SectionHeading id="quality" label="質問品質ランキング" icon={MessageSquareText} />
      <p className="text-sm text-muted-foreground mb-2">
        国会質疑の内容をAI（Claude Haiku）が分析し、質問の生産性を評価したランキングです。
      </p>
      <Screenshot src="/guide/quality-ranking.png" alt="質問品質ランキング" caption="質問品質ランキング — TOP3ハイライトとTOP100テーブル" />
      <h3 className="text-base font-semibold mt-6 mb-2">AI評価の4軸</h3>
      <FeatureList items={[
        { title: "政策的関連性", desc: "法案・予算・制度に直接関わる質問か" },
        { title: "建設性", desc: "具体的な改善提案を伴っているか" },
        { title: "専門性", desc: "独自の調査・データに基づいているか" },
        { title: "国益貢献度", desc: "国民生活・経済・安全保障に直結するか" },
      ]} />

      {/* ===== 7. お気に入り ===== */}
      <SectionHeading id="favorites" label="お気に入り" icon={Star} />
      <p className="text-sm text-muted-foreground mb-2">
        お気に入りに登録した議員をまとめて閲覧するページです。
      </p>
      <Screenshot src="/guide/favorites-desktop.png" alt="お気に入り" caption="お気に入り — 未登録時の空状態表示" />
      <FeatureList items={[
        { title: "登録方法", desc: "各ページの議員名横の☆ボタンをクリック" },
        { title: "CSV出力", desc: "お気に入り議員のスコアデータをCSVダウンロード" },
        { title: "比較に追加", desc: "選択した議員を比較ページに送る" },
      ]} />
      <Tip>お気に入りはブラウザのlocalStorageに保存されます。アカウント登録は不要です。</Tip>

      {/* ===== 8. 法案一覧 ===== */}
      <SectionHeading id="bills" label="法案一覧" icon={FileText} />
      <p className="text-sm text-muted-foreground mb-2">
        国会に提出された法案を検索・閲覧するページです。
      </p>
      <Screenshot src="/guide/bills-desktop.png" alt="法案一覧" caption="法案一覧 — フィルタ・ステータス分布バー・法案カード" />
      <FeatureList items={[
        { title: "法案名検索", desc: "タイトル部分一致で検索。一致箇所が黄色ハイライト" },
        { title: "種別フィルタ", desc: "閣法（政府提出）/ 衆法 / 参法（議員提出）" },
        { title: "状態フィルタ", desc: "成立 / 審議中 / 否決 / 未定 など" },
        { title: "カード左端の色", desc: "青=閣法、紫=衆法、琥珀=参法" },
      ]} />

      {/* ===== 9. 法案詳細 ===== */}
      <SectionHeading id="bill-detail" label="法案詳細" icon={FileSearch} />
      <p className="text-sm text-muted-foreground mb-2">
        個別の法案の詳細情報と投票結果を確認できるページです。パンくずリスト付き。
      </p>
      <Screenshot src="/guide/bill-detail-desktop.png" alt="法案詳細" caption="法案詳細 — 基本情報・投票結果（円グラフ・棒グラフ）" />

      {/* ===== 10. スコアについて ===== */}
      <SectionHeading id="about" label="スコアについて" icon={BookOpen} />
      <p className="text-sm text-muted-foreground mb-2">
        GiinScoreのスコアリング手法、評価の原則、データソース、限界について詳しく説明しているページです。
      </p>
      <Screenshot src="/guide/about-desktop.png" alt="スコアについて" caption="スコアについて — 評価の原則・5軸スコアの説明" />
      <p className="text-sm text-muted-foreground">
        詳しくは <Link href="/about" className="text-blue-600 dark:text-blue-400 hover:underline">スコアについて</Link> ページをご覧ください。
      </p>

      {/* ===== 11. モバイル ===== */}
      <SectionHeading id="mobile" label="モバイル対応" icon={Monitor} />
      <p className="text-sm text-muted-foreground mb-2">
        全ページがスマートフォン・タブレットに対応したレスポンシブデザインです。
      </p>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 my-6">
        <Screenshot src="/guide/home-mobile.png" alt="ホーム モバイル" caption="ホーム" />
        <Screenshot src="/guide/members-mobile.png" alt="議員一覧 モバイル" caption="議員一覧" />
        <Screenshot src="/guide/bills-mobile.png" alt="法案一覧 モバイル" caption="法案一覧" />
      </div>
      <FeatureList items={[
        { title: "ナビゲーション", desc: "ハンバーガーメニューからサイドシートで表示" },
        { title: "カードレイアウト", desc: "1列表示に自動切り替え" },
        { title: "テーブル", desc: "横スクロール対応。一部列が自動非表示" },
        { title: "グラフ", desc: "画面幅に合わせて自動リサイズ" },
      ]} />

      {/* ===== 12. ダークモード ===== */}
      <SectionHeading id="dark" label="ダークモード" icon={Moon} />
      <p className="text-sm text-muted-foreground mb-2">
        ヘッダー右上の月/太陽アイコンでダークモードに切り替えられます。OSの設定にも自動追従します。
      </p>
      <Screenshot src="/guide/home-dark.png" alt="ダークモード ホーム" caption="ダークモード — ホーム画面" />
      <Screenshot src="/guide/members-dark.png" alt="ダークモード 議員一覧" caption="ダークモード — 議員一覧" />

      {/* ===== グレード一覧 ===== */}
      <h2 className="text-xl font-bold text-foreground mt-14 mb-4 scroll-mt-20">グレード一覧</h2>
      <div className="grid grid-cols-5 gap-2 mb-6">
        {([
          { grade: "A", range: "80〜100", color: "bg-emerald-500", desc: "非常に高い活動" },
          { grade: "B", range: "60〜79",  color: "bg-blue-500",    desc: "平均以上" },
          { grade: "C", range: "40〜59",  color: "bg-yellow-500",  desc: "平均的" },
          { grade: "D", range: "20〜39",  color: "bg-orange-500",  desc: "平均以下" },
          { grade: "F", range: "0〜19",   color: "bg-red-500",     desc: "非常に低い" },
        ]).map(({ grade, range, color, desc }) => (
          <div key={grade} className="text-center">
            <div className={`mx-auto h-10 w-10 rounded-full ${color} flex items-center justify-center text-white font-bold mb-1.5 grade-badge`}>
              {grade}
            </div>
            <p className="text-xs font-medium text-foreground">{range}</p>
            <p className="text-[10px] text-muted-foreground">{desc}</p>
          </div>
        ))}
      </div>

      {/* ===== フッター ===== */}
      <div className="mt-16 pt-8 border-t text-center">
        <p className="text-sm text-muted-foreground mb-3">
          他にご不明な点があれば、お気軽にお問い合わせください。
        </p>
        <div className="flex justify-center gap-3">
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
          >
            <Trophy className="h-3.5 w-3.5" />
            ランキングを見る
          </Link>
          <Link
            href="/about"
            className="inline-flex items-center gap-1.5 rounded-lg border px-4 py-2 text-sm font-medium text-foreground hover:bg-muted/50 transition-colors"
          >
            <BookOpen className="h-3.5 w-3.5" />
            スコアについて
          </Link>
        </div>
      </div>
    </div>
  );
}
