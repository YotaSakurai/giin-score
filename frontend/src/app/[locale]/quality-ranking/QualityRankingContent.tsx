"use client";

import { useCallback } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Link } from "@/i18n/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { LoadingSpinner } from "@/components/ui/loading";
import { ErrorMessage } from "@/components/ui/error";
import { CHAMBER_LABELS, GRADE_COLORS } from "@/lib/types";
import { useRanking, useParties } from "@/lib/hooks";
import { ShareButton } from "@/components/ShareButton";

export default function QualityRankingContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const chamber = searchParams.get("chamber") || "all";
  const party = searchParams.get("party") || "all";
  const sortBy = searchParams.get("sort_by") || "question_quality";

  const chamberParam = chamber === "all" ? undefined : chamber;
  const partyParam = party === "all" ? undefined : party;

  const { data: parties } = useParties(chamberParam);

  const { data, error, isLoading, mutate } = useRanking({
    chamber: chamberParam,
    party: partyParam,
    sort_by: sortBy,
    sort_order: "desc",
    limit: 100,
  });

  const ranking = data?.items ?? [];

  const updateParams = useCallback(
    (updates: Record<string, string | undefined>) => {
      const params = new URLSearchParams(searchParams.toString());
      Object.entries(updates).forEach(([key, value]) => {
        if (value === undefined || value === "" || value === "all") {
          params.delete(key);
        } else {
          params.set(key, value);
        }
      });
      const qs = params.toString();
      router.push(qs ? `/quality-ranking?${qs}` : "/quality-ranking");
    },
    [router, searchParams],
  );

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <h1 className="text-2xl font-bold text-foreground">質問品質ランキング</h1>
          <ShareButton title="質問品質ランキング | GiinScore" />
        </div>
        <p className="text-sm text-muted-foreground">
          国会での質疑内容をAI分析し、政策的妥当性・建設性・専門性・国益への貢献度を評価したランキングです
        </p>
      </div>

      {/* フィルタ */}
      <div className="flex items-center gap-4 mb-6 flex-wrap">
        <Select value={chamber} onValueChange={(v) => updateParams({ chamber: v === "all" ? undefined : v })}>
          <SelectTrigger className="w-40" aria-label="院を選択">
            <SelectValue placeholder="院を選択" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全て</SelectItem>
            <SelectItem value="representatives">衆議院</SelectItem>
            <SelectItem value="councillors">参議院</SelectItem>
          </SelectContent>
        </Select>
        <Select value={party} onValueChange={(v) => updateParams({ party: v === "all" ? undefined : v })}>
          <SelectTrigger className="w-48" aria-label="政党を選択">
            <SelectValue placeholder="政党を選択" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全政党</SelectItem>
            {(parties ?? []).map((p) => (
              <SelectItem key={p} value={p}>{p}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={sortBy} onValueChange={(v) => updateParams({ sort_by: v === "question_quality" ? undefined : v })}>
          <SelectTrigger className="w-48" aria-label="ソート軸">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="question_quality">質問品質順</SelectItem>
            <SelectItem value="legislative_activity">立法活動順</SelectItem>
            <SelectItem value="policy_influence">政策影響力順</SelectItem>
            <SelectItem value="transparency">透明性順</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* ランキング説明 */}
      <Card className="mb-6 bg-slate-50 dark:bg-slate-900/50">
        <CardContent className="p-4">
          <p className="text-xs text-muted-foreground">
            質問品質スコアは、国会での発言内容をAIが分析し、①政策的関連性 ②建設性（対案や改善提案の有無）③専門性 ④国益への直接的貢献度 の4軸で評価した結果です。
            スキャンダル追及のみの質問やパフォーマンス質問は低評価となります。
          </p>
        </CardContent>
      </Card>

      {isLoading ? (
        <LoadingSpinner />
      ) : error ? (
        <ErrorMessage
          message={error instanceof Error ? error.message : "データの取得に失敗しました"}
          onRetry={() => mutate()}
        />
      ) : (
        <>
          {/* TOP3 */}
          {ranking.length >= 3 && (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
              {ranking.slice(0, 3).map((entry, idx) => {
                const colors = ["border-yellow-400 bg-yellow-50 dark:bg-yellow-950/30", "border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-800/50", "border-amber-600 bg-amber-50 dark:bg-amber-950/30"];
                const medals = ["\u{1F947}", "\u{1F948}", "\u{1F949}"];
                const qqScore = entry.score.question_quality;
                return (
                  <Card key={entry.member.id} className={`border-2 ${colors[idx]}`}>
                    <CardContent className="p-4">
                      <div className="flex items-center gap-3 mb-2">
                        <span className="text-2xl">{medals[idx]}</span>
                        <div className="flex-1 min-w-0">
                          <Link href={`/members/${entry.member.id}`} className="text-sm font-bold text-blue-600 hover:underline truncate block">
                            {entry.member.name}
                          </Link>
                          <p className="text-xs text-muted-foreground truncate">{entry.member.party ?? "無所属"}</p>
                        </div>
                      </div>
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-xs text-muted-foreground">質問品質</p>
                          <p className="text-xl font-bold">{qqScore.toFixed(1)}</p>
                        </div>
                        <div className="text-right">
                          <p className="text-xs text-muted-foreground">総合</p>
                          <p className="text-sm text-muted-foreground">{entry.score.total.toFixed(1)}</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}

          {/* モバイルカード */}
          <div className="sm:hidden space-y-3">
            {ranking.map((entry) => {
              const gradeColor = GRADE_COLORS[entry.score.grade] || "bg-gray-300";
              return (
                <Card key={entry.member.id}>
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <span className="text-lg font-bold text-muted-foreground w-8 text-right">{entry.rank}</span>
                      <span className={`inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-white text-sm font-bold ${gradeColor}`}>
                        {entry.score.grade}
                      </span>
                      <div className="flex-1 min-w-0">
                        <Link href={`/members/${entry.member.id}`} className="text-sm font-bold text-blue-600 hover:underline">
                          {entry.member.name}
                        </Link>
                        <p className="text-xs text-muted-foreground mt-0.5">{entry.member.party ?? "無所属"}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-bold text-rose-600">{entry.score.question_quality.toFixed(1)}</p>
                        <p className="text-xs text-muted-foreground">総合 {entry.score.total.toFixed(1)}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>

          {/* テーブル */}
          <Card className="hidden sm:block">
            <CardHeader>
              <CardTitle className="text-base">TOP {ranking.length}</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b bg-muted/50 text-left text-xs text-muted-foreground">
                      <th scope="col" className="p-3 w-12">#</th>
                      <th scope="col" className="p-3">議員名</th>
                      <th scope="col" className="p-3">政党</th>
                      <th scope="col" className="p-3 hidden md:table-cell">院</th>
                      <th scope="col" className="p-3 text-center">グレード</th>
                      <th scope="col" className="p-3 text-right font-bold">質問品質</th>
                      <th scope="col" className="p-3 text-right">総合</th>
                      <th scope="col" className="p-3 hidden lg:table-cell text-right">立法</th>
                      <th scope="col" className="p-3 hidden lg:table-cell text-right">影響力</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ranking.map((entry) => {
                      const gradeColor = GRADE_COLORS[entry.score.grade] || "bg-gray-300";
                      return (
                        <tr key={entry.member.id} className="border-b hover:bg-muted/50 transition-colors">
                          <td className="p-3 text-sm font-medium text-muted-foreground">{entry.rank}</td>
                          <td className="p-3">
                            <Link href={`/members/${entry.member.id}`} className="text-sm font-medium text-blue-600 hover:underline">
                              {entry.member.name}
                            </Link>
                          </td>
                          <td className="p-3 text-sm text-muted-foreground">{entry.member.party ?? "無所属"}</td>
                          <td className="p-3 hidden md:table-cell">
                            <Badge variant="outline" className="text-xs">{CHAMBER_LABELS[entry.member.chamber]}</Badge>
                          </td>
                          <td className="p-3 text-center">
                            <span className={`inline-flex h-7 w-7 items-center justify-center rounded-full text-white text-xs font-bold ${gradeColor}`}>
                              {entry.score.grade}
                            </span>
                          </td>
                          <td className="p-3 text-right">
                            <div className="flex items-center justify-end gap-2">
                              <div className="w-16 h-1.5 rounded-full bg-muted hidden md:block">
                                <div className="h-1.5 rounded-full bg-rose-500" style={{ width: `${Math.min(entry.score.question_quality, 100)}%` }} />
                              </div>
                              <span className="text-sm font-bold text-rose-600">{entry.score.question_quality.toFixed(1)}</span>
                            </div>
                          </td>
                          <td className="p-3 text-right text-sm text-muted-foreground">{entry.score.total.toFixed(1)}</td>
                          <td className="p-3 hidden lg:table-cell text-right text-xs text-muted-foreground">{entry.score.legislative_activity.toFixed(0)}</td>
                          <td className="p-3 hidden lg:table-cell text-right text-xs text-muted-foreground">{entry.score.policy_influence.toFixed(0)}</td>
                        </tr>
                      );
                    })}
                    {ranking.length === 0 && (
                      <tr>
                        <td colSpan={9} className="p-8 text-center text-sm text-muted-foreground">
                          データがまだありません
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
