import type { Metadata } from "next";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

export const metadata: Metadata = {
  title: "スコア算出方法",
  description:
    "GiinScoreのスコアリング手法・5軸スコア・正規化方法・データソース・限界について説明します。",
};

export default function AboutPage() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <h1 className="text-2xl font-bold text-foreground mb-2">スコア算出方法</h1>
      <p className="text-sm text-muted-foreground mb-8">GiinScoreのスコアリング手法と、その限界について説明します</p>

      {/* 免責表示 */}
      <div className="mb-8 rounded-lg bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 px-4 py-3">
        <p className="text-sm text-amber-800 dark:text-amber-200 font-medium mb-1">重要な注意事項</p>
        <p className="text-xs text-amber-700 dark:text-amber-300">
          本スコアは国会の公開データに基づく活動量の可視化であり、政治家の能力・人格・政策の正しさを評価するものではありません。
          スコアはあくまで「何をどれだけやったか」という量的指標であり、政策の質や正当性を評価するものではありません。
        </p>
      </div>

      {/* 5軸スコア説明 */}
      <h2 className="text-xl font-bold text-foreground mb-4">5軸スコア</h2>
      <p className="text-sm text-muted-foreground mb-6">
        GiinScoreは、イデオロギーフリーの設計原則に基づき、以下の5つの軸で議員の活動を定量化します。
        政策の「方向性」ではなく「行動量と質」を計測します。
      </p>

      <div className="space-y-4 mb-8">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">1. 立法活動スコア (LAS) - デフォルト重み: 25%</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground space-y-2">
            <p>法案の発議と委員会での質疑活動を計測します。</p>
            <ul className="list-disc pl-5 space-y-1">
              <li>法案発議数（筆頭発議者: 1.0, 共同5名以下: 0.5, 6-20名: 0.3, 21名超: 0.1）× (1 + 成立率)</li>
              <li>委員会質疑回数 × 質疑密度係数（平均発言文字数 / 基準値3000, 上限2.0）</li>
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">2. 投票行動スコア (VBS) - デフォルト重み: 20%</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground space-y-2">
            <p>投票への参加率を計測します。</p>
            <ul className="list-disc pl-5 space-y-1">
              <li>投票参加率 = 投票参加数 / 投票機会総数 × 100</li>
              <li>棄権は意思表示として参加カウント</li>
              <li>欠席は非参加としてカウント</li>
              <li>注: 党議拘束に従った投票か造反かの情報は表示しますが、スコアには加算しません</li>
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">3. 政策影響力スコア (PIS) - デフォルト重み: 20%</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground space-y-2">
            <p>発議した法案の成立度合いを計測します。</p>
            <ul className="list-disc pl-5 space-y-1">
              <li>成立法案への貢献（新規立法: 1.0, 大規模改正: 0.7, 軽微改正: 0.3）</li>
              <li>質問主意書提出数 × 0.3</li>
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">4. 透明性スコア (TS) - デフォルト重み: 15%</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground space-y-2">
            <p>公開活動への参加度を計測します。</p>
            <ul className="list-disc pl-5 space-y-1">
              <li>委員会発言回数 / 全委員会開催数 × 100</li>
              <li>委員会の多様性（異なる委員会への参加率）</li>
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">5. 質問品質スコア (QQS) - デフォルト重み: 20%</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground space-y-2">
            <p>国会での質疑内容をAI（Claude Haiku）が分析し、質の高い政策議論ができているかを評価します。</p>
            <ul className="list-disc pl-5 space-y-1">
              <li>政策的関連性: 国民生活・経済・安全保障に直接影響する政策課題か</li>
              <li>建設性: 対案や改善提案を伴う質問か（スキャンダル追及のみは低評価）</li>
              <li>専門性: 独自の調査・データに基づく追及か</li>
              <li>国益貢献度: 国力向上・国民生活改善への直接的な貢献度</li>
            </ul>
            <p className="mt-2 text-xs">※ 各発言の4軸スコア平均が質問品質の基礎値となります</p>
          </CardContent>
        </Card>
      </div>

      <Separator className="my-8" />

      {/* 正規化とグレード */}
      <h2 className="text-xl font-bold text-foreground mb-4">正規化手法</h2>
      <Card className="mb-8">
        <CardContent className="p-6 text-sm text-muted-foreground space-y-2">
          <p><strong>パーセンタイルランク方式</strong>を採用しています。</p>
          <ul className="list-disc pl-5 space-y-1">
            <li>比較群: 同一会期 × 同一院（衆/参） × 同一role_category</li>
            <li>role_category: 閣僚 / 与党一般 / 野党幹部 / 野党一般 / 委員長等</li>
            <li>各軸を0-100に正規化</li>
            <li>パーセンタイル = (自分より低い人数 / 比較群総数) × 100</li>
          </ul>
          <p className="mt-4"><strong>総合スコア</strong> = LAS×0.25 + VBS×0.20 + PIS×0.20 + TS×0.15 + QQS×0.20</p>
          <p className="text-xs text-muted-foreground mt-2">※ 重みはユーザーがスライダーで自由に変更できます</p>
        </CardContent>
      </Card>

      <h2 className="text-xl font-bold text-foreground mb-4">グレード</h2>
      <div className="grid grid-cols-5 gap-2 mb-8">
        {[
          { grade: "A", range: "80-100", color: "bg-emerald-500" },
          { grade: "B", range: "60-79", color: "bg-blue-500" },
          { grade: "C", range: "40-59", color: "bg-yellow-500" },
          { grade: "D", range: "20-39", color: "bg-orange-500" },
          { grade: "F", range: "0-19", color: "bg-red-500" },
        ].map(({ grade, range, color }) => (
          <Card key={grade} className="text-center">
            <CardContent className="p-4">
              <div className={`mx-auto h-10 w-10 rounded-full ${color} flex items-center justify-center text-white font-bold mb-2`}>
                {grade}
              </div>
              <p className="text-xs text-muted-foreground">{range}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Separator className="my-8" />

      {/* デフォルト重みの根拠 */}
      <h2 className="text-xl font-bold text-foreground mb-4">デフォルト重みの根拠</h2>
      <Card className="mb-8">
        <CardContent className="p-6 text-sm text-muted-foreground space-y-2">
          <p>デフォルトの重み配分（LAS 25%, VBS 20%, PIS 20%, TS 15%, QQS 20%）は以下の考え方に基づいています:</p>
          <ul className="list-disc pl-5 space-y-1">
            <li><strong>立法活動 (25%)</strong>: 議員の本来的職務である立法に最大の重みを付与</li>
            <li><strong>投票行動 (20%)</strong>: 国民の代理としての投票は基本的義務</li>
            <li><strong>政策影響力 (20%)</strong>: 実際の政策実現への貢献度</li>
            <li><strong>透明性 (15%)</strong>: データソースが限定的なため、やや低めに設定</li>
            <li><strong>質問品質 (20%)</strong>: 国会質疑の質はサービス理念「質疑時間の生産性」に直結する重要指標</li>
          </ul>
          <p className="mt-2">ユーザーはスライダーでこの重みを自由に変更でき、自分の価値観に基づいた評価が可能です。</p>
        </CardContent>
      </Card>

      <Separator className="my-8" />

      {/* データソース */}
      <h2 className="text-xl font-bold text-foreground mb-4">データソース</h2>
      <Card className="mb-8">
        <CardContent className="p-6">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-muted-foreground">
                  <th scope="col" className="pb-2">データ</th>
                  <th scope="col" className="pb-2">ソース</th>
                  <th scope="col" className="pb-2">取得方法</th>
                </tr>
              </thead>
              <tbody className="text-muted-foreground">
                <tr className="border-b">
                  <td className="py-2">発言記録</td>
                  <td>国会会議録API (kokkai.ndl.go.jp)</td>
                  <td>REST API</td>
                </tr>
                <tr className="border-b">
                  <td className="py-2">法案情報</td>
                  <td>SmartNews SMRI GitHub (CSV)</td>
                  <td>ダウンロード</td>
                </tr>
                <tr className="border-b">
                  <td className="py-2">議案詳細・提出者</td>
                  <td>衆議院Webサイト (shugiin.go.jp)</td>
                  <td>スクレイピング</td>
                </tr>
                <tr className="border-b">
                  <td className="py-2">投票記録</td>
                  <td>参議院Webサイト (sangiin.go.jp)</td>
                  <td>スクレイピング</td>
                </tr>
                <tr className="border-b">
                  <td className="py-2">質問主意書</td>
                  <td>参議院Webサイト (sangiin.go.jp)</td>
                  <td>スクレイピング</td>
                </tr>
                <tr className="border-b">
                  <td className="py-2">議員プロフィール</td>
                  <td>衆議院・参議院Webサイト</td>
                  <td>スクレイピング</td>
                </tr>
                <tr>
                  <td className="py-2">質問品質分析</td>
                  <td>Claude Haiku (AI分析)</td>
                  <td>LLM API</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p className="text-xs text-muted-foreground mt-4">
            データは週次で自動更新されます。最終更新日はフッターに表示しています。
          </p>
        </CardContent>
      </Card>

      <Separator className="my-8" />

      {/* 限界 */}
      <h2 className="text-xl font-bold text-foreground mb-4">スコアの限界</h2>
      <Card>
        <CardContent className="p-6 text-sm text-muted-foreground space-y-2">
          <ul className="list-disc pl-5 space-y-2">
            <li>量的指標のみを計測しており、政策の質・妥当性・影響力の深さは評価できません</li>
            <li>議員の活動は国会内に限らず、地元活動・政党内活動・外交活動等は含まれません</li>
            <li>閣僚や委員長は立場上、法案発議や質疑の機会が構造的に異なります（role_categoryによる正規化で緩和）</li>
            <li>データソースの更新頻度や欠損により、一部のデータが反映されない場合があります</li>
            <li>議員名の名寄せ（同一人物の特定）に誤りが含まれる可能性があります</li>
            <li>スクレイピング対象サイトのHTML構造変更により、一時的にデータ取得が停止する可能性があります</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
