import type { Metadata } from "next";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

export const metadata: Metadata = {
  title: "API ドキュメント",
  description:
    "GiinScore公開APIの利用ガイド。議員スコア・ランキング・法案データにプログラムからアクセスできます。",
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://api.giin-score.com/api/v1";

interface EndpointProps {
  method: string;
  path: string;
  summary: string;
  description: string;
  params?: { name: string; type: string; required: boolean; description: string }[];
  responseExample?: string;
}

function Endpoint({ method, path, summary, description, params, responseExample }: EndpointProps) {
  return (
    <Card className="mb-4">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2 flex-wrap">
          <Badge variant="secondary" className="bg-emerald-100 text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-300 font-mono text-xs">
            {method}
          </Badge>
          <code className="text-sm font-mono text-foreground">{path}</code>
        </div>
        <CardTitle className="text-base mt-1">{summary}</CardTitle>
      </CardHeader>
      <CardContent className="text-sm text-muted-foreground space-y-3">
        <p>{description}</p>

        {params && params.length > 0 && (
          <div>
            <p className="font-medium text-foreground text-xs mb-2">パラメータ</p>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th scope="col" className="pb-1 pr-4">名前</th>
                    <th scope="col" className="pb-1 pr-4">型</th>
                    <th scope="col" className="pb-1 pr-4">必須</th>
                    <th scope="col" className="pb-1">説明</th>
                  </tr>
                </thead>
                <tbody>
                  {params.map((p) => (
                    <tr key={p.name} className="border-b">
                      <td className="py-1.5 pr-4 font-mono">{p.name}</td>
                      <td className="py-1.5 pr-4">{p.type}</td>
                      <td className="py-1.5 pr-4">{p.required ? "Yes" : "No"}</td>
                      <td className="py-1.5">{p.description}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {responseExample && (
          <div>
            <p className="font-medium text-foreground text-xs mb-2">レスポンス例</p>
            <pre className="bg-muted rounded-lg p-3 text-xs overflow-x-auto">
              <code>{responseExample}</code>
            </pre>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function ApiDocsPage() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <h1 className="text-2xl font-bold text-foreground mb-2">API ドキュメント</h1>
      <p className="text-sm text-muted-foreground mb-4">
        GiinScore APIを使って、議員スコア・ランキング・法案データにプログラムからアクセスできます。
      </p>

      {/* ベースURL */}
      <Card className="mb-8">
        <CardContent className="p-4">
          <p className="text-xs text-muted-foreground mb-1">ベースURL</p>
          <code className="text-sm font-mono text-foreground">{API_BASE}</code>
        </CardContent>
      </Card>

      {/* レート制限 */}
      <div className="mb-8 rounded-lg bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 px-4 py-3">
        <p className="text-sm text-amber-800 dark:text-amber-200 font-medium mb-1">レート制限</p>
        <p className="text-xs text-amber-700 dark:text-amber-300">
          APIリクエストは <strong>60リクエスト/分</strong> に制限されています。
          レスポンスヘッダーの <code className="bg-amber-100 dark:bg-amber-900 px-1 rounded">X-RateLimit-Limit</code> と{" "}
          <code className="bg-amber-100 dark:bg-amber-900 px-1 rounded">X-RateLimit-Remaining</code> で残り回数を確認できます。
        </p>
      </div>

      {/* OpenAPI */}
      <Card className="mb-8">
        <CardContent className="p-4 flex items-center gap-4">
          <div>
            <p className="text-sm font-medium text-foreground">OpenAPI (Swagger UI)</p>
            <p className="text-xs text-muted-foreground">
              対話的にAPIを試せるSwagger UIも利用可能です。
            </p>
          </div>
          <a
            href={`${API_BASE.replace("/api/v1", "")}/docs`}
            target="_blank"
            rel="noopener noreferrer"
            className="ml-auto shrink-0 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
          >
            Swagger UI を開く
          </a>
        </CardContent>
      </Card>

      <Separator className="my-8" />

      {/* スコア関連 */}
      <h2 className="text-xl font-bold text-foreground mb-4">スコア・ランキング</h2>

      <Endpoint
        method="GET"
        path="/scores/ranking"
        summary="スコアランキング取得"
        description="議員スコアのランキングを返す。院・政党・会期でフィルタリングし、指定軸でソートした結果をページングで返す。"
        params={[
          { name: "chamber", type: "string", required: false, description: "representatives（衆議院）/ councillors（参議院）" },
          { name: "party", type: "string", required: false, description: "政党名でフィルタ" },
          { name: "session_number", type: "integer", required: false, description: "会期番号（未指定時は最新会期）" },
          { name: "sort_by", type: "string", required: false, description: "ソート軸: total / legislative_activity / voting_behavior / policy_influence / transparency" },
          { name: "limit", type: "integer", required: false, description: "取得件数（1-100, デフォルト20）" },
          { name: "offset", type: "integer", required: false, description: "オフセット（デフォルト0）" },
        ]}
        responseExample={`{
  "items": [
    {
      "rank": 1,
      "member": {
        "id": 123,
        "name": "山田太郎",
        "chamber": "representatives",
        "party": "○○党"
      },
      "score": {
        "total": 85.3,
        "grade": "A",
        "legislative_activity": 90.2,
        "voting_behavior": 78.5,
        "policy_influence": 82.1,
        "transparency": 88.7
      }
    }
  ],
  "total": 465
}`}
      />

      <Endpoint
        method="GET"
        path="/scores/stats"
        summary="スコア統計取得"
        description="スコアの統計情報（平均・中央値・分布）を返す。グレード別（A〜F）の人数分布も含む。"
        params={[
          { name: "chamber", type: "string", required: false, description: "representatives / councillors" },
          { name: "session_number", type: "integer", required: false, description: "会期番号" },
        ]}
      />

      <Endpoint
        method="GET"
        path="/scores/by-party"
        summary="政党別統計取得"
        description="政党別のスコア統計（平均・中央値・各軸平均）を返す。"
        params={[
          { name: "chamber", type: "string", required: false, description: "representatives / councillors" },
          { name: "session_number", type: "integer", required: false, description: "会期番号" },
        ]}
      />

      <Endpoint
        method="GET"
        path="/scores/export/csv"
        summary="ランキングCSVエクスポート"
        description="ランキングデータをCSV形式でダウンロードする。BOM付きUTF-8でExcel互換。"
        params={[
          { name: "chamber", type: "string", required: false, description: "representatives / councillors" },
          { name: "party", type: "string", required: false, description: "政党名" },
          { name: "session_number", type: "integer", required: false, description: "会期番号" },
        ]}
      />

      <Endpoint
        method="GET"
        path="/scores/parties"
        summary="政党一覧取得"
        description="データベースに存在する政党名の一覧を返す。"
        params={[
          { name: "chamber", type: "string", required: false, description: "representatives / councillors" },
        ]}
        responseExample={`["自由民主党", "立憲民主党", "日本維新の会", ...]`}
      />

      <Separator className="my-8" />

      {/* 議員関連 */}
      <h2 className="text-xl font-bold text-foreground mb-4">議員</h2>

      <Endpoint
        method="GET"
        path="/members"
        summary="議員一覧取得"
        description="議員一覧を最新スコア付きで返す。院・政党・選挙区・名前でフィルタリングし、スコア各軸でソート可能。"
        params={[
          { name: "chamber", type: "string", required: false, description: "representatives / councillors" },
          { name: "party", type: "string", required: false, description: "政党名" },
          { name: "search", type: "string", required: false, description: "議員名で部分一致検索" },
          { name: "district", type: "string", required: false, description: "選挙区名で部分一致検索" },
          { name: "sort_by", type: "string", required: false, description: "name / total / legislative_activity 等" },
          { name: "page", type: "integer", required: false, description: "ページ番号（デフォルト1）" },
          { name: "per_page", type: "integer", required: false, description: "1ページあたり件数（1-100, デフォルト20）" },
        ]}
      />

      <Endpoint
        method="GET"
        path="/members/{member_id}"
        summary="議員詳細取得"
        description="指定IDの議員詳細（プロフィール・全会期スコア）を返す。"
        params={[
          { name: "member_id", type: "integer", required: true, description: "議員ID" },
        ]}
      />

      <Endpoint
        method="GET"
        path="/members/{member_id}/speeches"
        summary="議員発言一覧取得"
        description="指定議員の国会発言一覧をページングで返す。"
        params={[
          { name: "member_id", type: "integer", required: true, description: "議員ID" },
          { name: "page", type: "integer", required: false, description: "ページ番号" },
          { name: "per_page", type: "integer", required: false, description: "1ページあたり件数" },
        ]}
      />

      <Endpoint
        method="GET"
        path="/members/{member_id}/votes"
        summary="議員投票記録取得"
        description="指定議員の投票記録をページングで返す。"
        params={[
          { name: "member_id", type: "integer", required: true, description: "議員ID" },
          { name: "page", type: "integer", required: false, description: "ページ番号" },
          { name: "per_page", type: "integer", required: false, description: "1ページあたり件数" },
        ]}
      />

      <Endpoint
        method="GET"
        path="/members/{member_id}/vote-pattern"
        summary="投票パターン分析"
        description="議員の投票パターン（造反率・参加率）を分析して返す。同じ政党の議員との比較に基づく。"
        params={[
          { name: "member_id", type: "integer", required: true, description: "議員ID" },
        ]}
        responseExample={`{
  "member_id": 123,
  "total_votes": 150,
  "dissent_votes": 3,
  "dissent_rate": 2.0,
  "participation_rate": 95.5,
  "absent_count": 8,
  "dissent_details": [
    {
      "bill_title": "○○法案",
      "member_vote": "nay",
      "party_majority_vote": "aye"
    }
  ]
}`}
      />

      <Endpoint
        method="GET"
        path="/members/districts"
        summary="選挙区一覧取得"
        description="データベースに存在する選挙区名の一覧を返す。"
        params={[
          { name: "chamber", type: "string", required: false, description: "representatives / councillors" },
        ]}
      />

      <Separator className="my-8" />

      {/* 法案関連 */}
      <h2 className="text-xl font-bold text-foreground mb-4">法案</h2>

      <Endpoint
        method="GET"
        path="/bills"
        summary="法案一覧取得"
        description="法案一覧を返す。会期・種別・状態・タイトル検索でフィルタリング可能。"
        params={[
          { name: "session_number", type: "integer", required: false, description: "会期番号" },
          { name: "bill_kind", type: "string", required: false, description: "法案種別" },
          { name: "status", type: "string", required: false, description: "法案状態" },
          { name: "search", type: "string", required: false, description: "タイトル検索" },
          { name: "page", type: "integer", required: false, description: "ページ番号" },
          { name: "per_page", type: "integer", required: false, description: "1ページあたり件数" },
        ]}
      />

      <Endpoint
        method="GET"
        path="/bills/{bill_id}"
        summary="法案詳細取得"
        description="指定IDの法案の詳細（提出者・投票結果含む）を返す。"
        params={[
          { name: "bill_id", type: "integer", required: true, description: "法案ID" },
        ]}
      />

      <Separator className="my-8" />

      {/* その他 */}
      <h2 className="text-xl font-bold text-foreground mb-4">その他</h2>

      <Endpoint
        method="GET"
        path="/sessions"
        summary="会期一覧取得"
        description="登録されている国会会期一覧を降順で返す。"
      />

      <Endpoint
        method="GET"
        path="/data-quality"
        summary="データ品質概要取得"
        description="会期ごとのデータ充足状況（スコア済み議員数・発言数・法案数・投票数）を返す。"
      />

      <Endpoint
        method="GET"
        path="/health"
        summary="ヘルスチェック"
        description="APIサーバーとデータベースの接続状態を返す。"
        responseExample={`{"status": "ok", "database": "connected"}`}
      />

      <Separator className="my-8" />

      {/* 使い方 */}
      <h2 className="text-xl font-bold text-foreground mb-4">使い方の例</h2>
      <Card>
        <CardContent className="p-4 space-y-4">
          <div>
            <p className="text-xs font-medium text-foreground mb-1">cURL</p>
            <pre className="bg-muted rounded-lg p-3 text-xs overflow-x-auto">
              <code>{`curl "${API_BASE}/scores/ranking?chamber=representatives&limit=10"`}</code>
            </pre>
          </div>
          <div>
            <p className="text-xs font-medium text-foreground mb-1">Python</p>
            <pre className="bg-muted rounded-lg p-3 text-xs overflow-x-auto">
              <code>{`import requests

response = requests.get(
    "${API_BASE}/scores/ranking",
    params={"chamber": "representatives", "limit": 10}
)
data = response.json()
for item in data["items"]:
    print(f"{item['rank']}. {item['member']['name']} - {item['score']['total']}")`}</code>
            </pre>
          </div>
          <div>
            <p className="text-xs font-medium text-foreground mb-1">JavaScript (fetch)</p>
            <pre className="bg-muted rounded-lg p-3 text-xs overflow-x-auto">
              <code>{`const res = await fetch(
  "${API_BASE}/scores/ranking?chamber=representatives&limit=10"
);
const data = await res.json();
data.items.forEach(item => {
  console.log(\`\${item.rank}. \${item.member.name} - \${item.score.total}\`);
});`}</code>
            </pre>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
