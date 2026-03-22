"use client";

import { useCallback } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { LoadingSpinner } from "@/components/ui/loading";
import { ErrorMessage } from "@/components/ui/error";
import { AXIS_LABELS } from "@/lib/types";
import { usePartyStats } from "@/lib/hooks";
import { ShareButton } from "@/components/ShareButton";
import { PartyBarChart } from "@/components/score/PartyBarChart";

export default function PartyStatsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const chamber = searchParams.get("chamber") || "all";

  const chamberParam = chamber === "all" ? undefined : chamber;

  const {
    data,
    error,
    isLoading,
    mutate,
  } = usePartyStats({ chamber: chamberParam });

  const setChamber = useCallback(
    (value: string) => {
      const params = new URLSearchParams(searchParams.toString());
      if (value === "all") {
        params.delete("chamber");
      } else {
        params.set("chamber", value);
      }
      const qs = params.toString();
      router.push(qs ? `/parties?${qs}` : "/parties");
    },
    [router, searchParams],
  );

  const items = data?.items ?? [];

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      {/* ヘッダー */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <h1 className="text-2xl font-bold text-foreground">政党別統計</h1>
          <ShareButton title="政党別統計 | GiinScore" />
        </div>
        <p className="text-sm text-muted-foreground">
          政党ごとの議員活動スコア平均・分布を比較
        </p>
      </div>

      {/* フィルタ */}
      <div className="flex items-center gap-4 mb-6">
        <Select value={chamber} onValueChange={setChamber}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="院を選択" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全て</SelectItem>
            <SelectItem value="representatives">衆議院</SelectItem>
            <SelectItem value="councillors">参議院</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {isLoading ? (
        <LoadingSpinner />
      ) : error ? (
        <ErrorMessage
          message={error instanceof Error ? error.message : "データの取得に失敗しました"}
          onRetry={() => mutate()}
        />
      ) : (
        <>
          {/* 棒グラフ */}
          <Card className="mb-6">
            <CardHeader>
              <CardTitle className="text-base">平均スコア比較</CardTitle>
            </CardHeader>
            <CardContent>
              <PartyBarChart items={items} />
            </CardContent>
          </Card>

          {/* テーブル */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">政党別詳細</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b bg-muted/50 text-left text-xs text-muted-foreground">
                      <th scope="col" className="p-3">#</th>
                      <th scope="col" className="p-3">政党</th>
                      <th scope="col" className="p-3 text-right">議員数</th>
                      <th scope="col" className="p-3 text-right">平均スコア</th>
                      <th scope="col" className="p-3 text-right hidden sm:table-cell">中央値</th>
                      <th scope="col" className="p-3 text-right hidden md:table-cell">最高</th>
                      <th scope="col" className="p-3 text-right hidden md:table-cell">最低</th>
                      <th scope="col" className="p-3 text-right hidden lg:table-cell">
                        {AXIS_LABELS.legislative_activity}
                      </th>
                      <th scope="col" className="p-3 text-right hidden lg:table-cell">
                        {AXIS_LABELS.voting_behavior}
                      </th>
                      <th scope="col" className="p-3 text-right hidden lg:table-cell">
                        {AXIS_LABELS.policy_influence}
                      </th>
                      <th scope="col" className="p-3 text-right hidden lg:table-cell">
                        {AXIS_LABELS.transparency}
                      </th>
                      <th scope="col" className="p-3 text-right hidden lg:table-cell">
                        {AXIS_LABELS.question_quality}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map((entry, idx) => (
                      <tr key={entry.party} className="border-b hover:bg-muted/50 transition-colors">
                        <td className="p-3 text-sm font-medium text-muted-foreground">{idx + 1}</td>
                        <td className="p-3 text-sm font-medium text-foreground">{entry.party}</td>
                        <td className="p-3 text-right text-sm text-muted-foreground">{entry.member_count}</td>
                        <td className="p-3 text-right text-sm font-bold">{entry.average_score.toFixed(1)}</td>
                        <td className="p-3 text-right text-sm text-muted-foreground hidden sm:table-cell">
                          {entry.median_score.toFixed(1)}
                        </td>
                        <td className="p-3 text-right text-sm text-emerald-600 hidden md:table-cell">
                          {entry.max_score.toFixed(1)}
                        </td>
                        <td className="p-3 text-right text-sm text-red-500 hidden md:table-cell">
                          {entry.min_score.toFixed(1)}
                        </td>
                        <td className="p-3 text-right text-xs text-muted-foreground hidden lg:table-cell">
                          {entry.average_legislative_activity.toFixed(1)}
                        </td>
                        <td className="p-3 text-right text-xs text-muted-foreground hidden lg:table-cell">
                          {entry.average_voting_behavior.toFixed(1)}
                        </td>
                        <td className="p-3 text-right text-xs text-muted-foreground hidden lg:table-cell">
                          {entry.average_policy_influence.toFixed(1)}
                        </td>
                        <td className="p-3 text-right text-xs text-muted-foreground hidden lg:table-cell">
                          {entry.average_transparency.toFixed(1)}
                        </td>
                        <td className="p-3 text-right text-xs text-muted-foreground hidden lg:table-cell">
                          {entry.average_question_quality.toFixed(1)}
                        </td>
                      </tr>
                    ))}
                    {items.length === 0 && (
                      <tr>
                        <td colSpan={12} className="p-8 text-center text-sm text-muted-foreground">
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
