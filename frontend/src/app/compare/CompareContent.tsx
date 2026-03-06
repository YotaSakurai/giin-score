"use client";

import { useSearchParams } from "next/navigation";
import Link from "next/link";
import useSWR from "swr";
import { swrFetcher } from "@/lib/api";
import type { MemberDetail } from "@/lib/types";
import { CHAMBER_LABELS, GRADE_COLORS, AXIS_LABELS } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { LoadingSpinner } from "@/components/ui/loading";
import { ErrorMessage } from "@/components/ui/error";
import { CompareRadarChart } from "@/components/score/CompareRadarChart";

const COMPARE_COLORS = [
  { stroke: "#3b82f6", fill: "#3b82f6" }, // blue
  { stroke: "#ef4444", fill: "#ef4444" }, // red
  { stroke: "#10b981", fill: "#10b981" }, // emerald
  { stroke: "#f59e0b", fill: "#f59e0b" }, // amber
];

const SCORE_AXES = [
  "legislative_activity",
  "voting_behavior",
  "policy_influence",
  "transparency",
] as const;

function useMemberDetail(id: number | null) {
  return useSWR<MemberDetail>(
    id !== null ? `/members/${id}` : null,
    swrFetcher
  );
}

export default function CompareContent() {
  const searchParams = useSearchParams();
  const idsParam = searchParams.get("ids") || "";
  const ids = idsParam
    .split(",")
    .map((s) => parseInt(s, 10))
    .filter((n) => !isNaN(n))
    .slice(0, 4);

  // 最大4名分の議員データを並列取得
  const member0 = useMemberDetail(ids[0] ?? null);
  const member1 = useMemberDetail(ids[1] ?? null);
  const member2 = useMemberDetail(ids[2] ?? null);
  const member3 = useMemberDetail(ids[3] ?? null);

  const results = [member0, member1, member2, member3].slice(0, ids.length);
  const isLoading = results.some((r) => r.isLoading);
  const error = results.find((r) => r.error)?.error;
  const members = results
    .map((r) => r.data)
    .filter((d): d is MemberDetail => d !== undefined);

  // 議員が未選択の場合
  if (ids.length === 0) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-8">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-foreground mb-2">議員比較</h1>
          <p className="text-sm text-muted-foreground">
            議員を選択して活動スコアを比較できます
          </p>
        </div>
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16">
            <svg
              className="h-16 w-16 text-muted-foreground/50 mb-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"
              />
            </svg>
            <p className="text-muted-foreground font-medium mb-2">
              比較する議員が選択されていません
            </p>
            <p className="text-sm text-muted-foreground mb-6">
              ランキングページから議員を選択してください
            </p>
            <Button asChild>
              <Link href="/">ランキングページへ</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-8">
        <LoadingSpinner />
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-8">
        <ErrorMessage
          message={
            error instanceof Error
              ? error.message
              : "データの取得に失敗しました"
          }
        />
      </div>
    );
  }

  // 各議員の最新スコアを取得
  const memberScores = members.map((m) => {
    const latest = m.scores.length > 0 ? m.scores[0] : null;
    return { member: m, score: latest };
  });

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground mb-2">議員比較</h1>
          <p className="text-sm text-muted-foreground">
            {members.map((m) => m.name).join(" / ")} の活動スコアを比較
          </p>
        </div>
        <Button variant="outline" asChild>
          <Link href="/">戻る</Link>
        </Button>
      </div>

      {/* レーダーチャート */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="text-base">スコア比較チャート</CardTitle>
        </CardHeader>
        <CardContent>
          {/* 凡例 */}
          <div className="flex flex-wrap gap-4 mb-4 justify-center">
            {memberScores.map((ms, idx) => (
              <div key={ms.member.id} className="flex items-center gap-2">
                <span
                  className="inline-block h-3 w-3 rounded-full"
                  style={{ backgroundColor: COMPARE_COLORS[idx].stroke }}
                />
                <span className="text-sm text-foreground/80">{ms.member.name}</span>
              </div>
            ))}
          </div>
          <CompareRadarChart
            members={memberScores.map((ms, idx) => ({
              name: ms.member.name,
              legislative_activity: ms.score?.legislative_activity ?? 0,
              voting_behavior: ms.score?.voting_behavior ?? 0,
              policy_influence: ms.score?.policy_influence ?? 0,
              transparency: ms.score?.transparency ?? 0,
              color: COMPARE_COLORS[idx],
            }))}
          />
        </CardContent>
      </Card>

      {/* 比較テーブル */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">スコア詳細比較</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-muted/50 text-left text-xs text-muted-foreground">
                  <th scope="col" className="p-3 min-w-[120px]">項目</th>
                  {memberScores.map((ms, idx) => (
                    <th
                      key={ms.member.id}
                      scope="col"
                      className="p-3 text-center min-w-[100px]"
                    >
                      <div className="flex items-center justify-center gap-1.5">
                        <span
                          className="inline-block h-2.5 w-2.5 rounded-full"
                          style={{
                            backgroundColor: COMPARE_COLORS[idx].stroke,
                          }}
                        />
                        <Link
                          href={`/members/${ms.member.id}`}
                          className="text-blue-600 hover:underline"
                        >
                          {ms.member.name}
                        </Link>
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {/* 基本情報 */}
                <tr className="border-b">
                  <td className="p-3 text-sm font-medium text-foreground/80">政党</td>
                  {memberScores.map((ms) => (
                    <td
                      key={ms.member.id}
                      className="p-3 text-center text-sm text-muted-foreground"
                    >
                      {ms.member.party ?? "無所属"}
                    </td>
                  ))}
                </tr>
                <tr className="border-b">
                  <td className="p-3 text-sm font-medium text-foreground/80">院</td>
                  {memberScores.map((ms) => (
                    <td key={ms.member.id} className="p-3 text-center">
                      <Badge variant="outline" className="text-xs">
                        {CHAMBER_LABELS[ms.member.chamber]}
                      </Badge>
                    </td>
                  ))}
                </tr>

                {/* グレード */}
                <tr className="border-b bg-muted/50/50">
                  <td className="p-3 text-sm font-medium text-foreground/80">
                    グレード
                  </td>
                  {memberScores.map((ms) => (
                    <td key={ms.member.id} className="p-3 text-center">
                      {ms.score ? (
                        <span
                          className={`inline-flex h-8 w-8 items-center justify-center rounded-full text-white text-sm font-bold ${GRADE_COLORS[ms.score.grade] || "bg-gray-300"}`}
                        >
                          {ms.score.grade}
                        </span>
                      ) : (
                        <span className="text-sm text-muted-foreground/70">-</span>
                      )}
                    </td>
                  ))}
                </tr>

                {/* 総合スコア */}
                <tr className="border-b bg-muted/50/50">
                  <td className="p-3 text-sm font-bold text-foreground">
                    総合スコア
                  </td>
                  {memberScores.map((ms) => (
                    <td
                      key={ms.member.id}
                      className="p-3 text-center text-lg font-bold"
                    >
                      {ms.score ? ms.score.total.toFixed(1) : "-"}
                    </td>
                  ))}
                </tr>

                {/* 各軸スコア */}
                {SCORE_AXES.map((axis) => {
                  const values = memberScores.map(
                    (ms) => ms.score?.[axis] ?? null
                  );
                  const validValues = values.filter(
                    (v): v is number => v !== null
                  );
                  const maxValue =
                    validValues.length > 0 ? Math.max(...validValues) : null;

                  return (
                    <tr key={axis} className="border-b">
                      <td className="p-3 text-sm font-medium text-foreground/80">
                        {AXIS_LABELS[axis]}
                      </td>
                      {memberScores.map((ms) => {
                        const value = ms.score?.[axis] ?? null;
                        const isMax =
                          value !== null &&
                          maxValue !== null &&
                          value === maxValue &&
                          validValues.length > 1;
                        return (
                          <td
                            key={ms.member.id}
                            className={`p-3 text-center text-sm ${isMax ? "font-bold text-blue-600" : "text-muted-foreground"}`}
                          >
                            {value !== null ? value.toFixed(1) : "-"}
                            {isMax && (
                              <span className="ml-1 text-xs text-blue-400">
                                &#9650;
                              </span>
                            )}
                          </td>
                        );
                      })}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
