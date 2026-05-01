"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Link } from "@/i18n/navigation";
import useSWR from "swr";
import { swrFetcher, buildQuery } from "@/lib/api";
import type { MemberDetail, MemberWithScore, PaginatedResponse } from "@/lib/types";
import { CHAMBER_LABELS, GRADE_COLORS, AXIS_LABELS } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { LoadingSpinner } from "@/components/ui/loading";
import { ErrorMessage } from "@/components/ui/error";
import { ShareButton } from "@/components/ShareButton";
import dynamic from "next/dynamic";

const CompareRadarChart = dynamic(
  () => import("@/components/score/CompareRadarChart").then(m => ({ default: m.CompareRadarChart })),
  { loading: () => <LoadingSpinner /> },
);

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
  "question_quality",
] as const;

type ScoreAxis = (typeof SCORE_AXES)[number] | "total";

const AXIS_BAR_COLORS: Record<string, string> = {
  legislative_activity: "bg-violet-500",
  voting_behavior: "bg-sky-500",
  policy_influence: "bg-emerald-500",
  transparency: "bg-amber-500",
  question_quality: "bg-rose-500",
  total: "bg-blue-600",
};

function ScoreBar({ value, maxInGroup, color }: { value: number; maxInGroup: number; color: string }) {
  const width = maxInGroup > 0 ? (value / maxInGroup) * 100 : 0;
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-3 bg-muted rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${width}%` }} />
      </div>
      <span className="text-xs font-medium w-10 text-right">{value.toFixed(1)}</span>
    </div>
  );
}

/** 議員検索フォーム for 比較ページ */
function CompareSearchInput({
  existingIds,
  onAdd,
}: {
  existingIds: number[];
  onAdd: (id: number) => void;
}) {
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [showSuggestions, setShowSuggestions] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  const containerRef = useRef<HTMLDivElement>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const v = e.target.value;
    setQuery(v);
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => setDebouncedQuery(v), 300);
    setShowSuggestions(v.length >= 1);
  };

  useEffect(() => () => clearTimeout(timerRef.current), []);

  const { data: suggestions } = useSWR<PaginatedResponse<MemberWithScore>>(
    debouncedQuery.length >= 1
      ? `/members${buildQuery({ search: debouncedQuery, per_page: 8 })}`
      : null,
    swrFetcher,
    { revalidateOnFocus: false, dedupingInterval: 1000 },
  );

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const items = (suggestions?.items ?? []).filter((m) => !existingIds.includes(m.id));

  return (
    <div ref={containerRef} className="relative w-full sm:w-72">
      <Input
        placeholder="議員名で検索して追加..."
        value={query}
        onChange={handleChange}
        onFocus={() => query.length >= 1 && setShowSuggestions(true)}
        disabled={existingIds.length >= 4}
      />
      {showSuggestions && items.length > 0 && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-popover border border-border rounded-lg shadow-lg z-50 max-h-60 overflow-auto">
          {items.map((m) => (
            <button
              key={m.id}
              type="button"
              className="w-full px-3 py-2 text-left hover:bg-muted/50 flex items-center gap-2 text-sm"
              onClick={() => {
                onAdd(m.id);
                setQuery("");
                setDebouncedQuery("");
                setShowSuggestions(false);
              }}
            >
              <span className="font-medium">{m.name}</span>
              <span className="text-xs text-muted-foreground">{m.party ?? "無所属"}</span>
              {m.latest_score && (
                <span className="ml-auto text-xs text-muted-foreground">
                  {m.latest_score.grade} {m.latest_score.total.toFixed(1)}
                </span>
              )}
            </button>
          ))}
        </div>
      )}
      {existingIds.length >= 4 && (
        <p className="text-xs text-muted-foreground mt-1">最大4名まで比較できます</p>
      )}
    </div>
  );
}

function useMemberDetail(id: number | null) {
  return useSWR<MemberDetail>(
    id !== null ? `/members/${id}` : null,
    swrFetcher
  );
}

export default function CompareContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const idsParam = searchParams.get("ids") || "";
  const ids = idsParam
    .split(",")
    .map((s) => parseInt(s, 10))
    .filter((n) => !isNaN(n))
    .slice(0, 4);

  const addMember = useCallback(
    (id: number) => {
      if (ids.includes(id) || ids.length >= 4) return;
      const newIds = [...ids, id];
      router.push(`/compare?ids=${newIds.join(",")}`);
    },
    [ids, router],
  );

  const removeMember = useCallback(
    (id: number) => {
      const newIds = ids.filter((x) => x !== id);
      if (newIds.length === 0) {
        router.push("/compare");
      } else {
        router.push(`/compare?ids=${newIds.join(",")}`);
      }
    },
    [ids, router],
  );

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
              比較する議員を検索してください
            </p>
            <div className="mb-4">
              <CompareSearchInput existingIds={ids} onAdd={addMember} />
            </div>
            <p className="text-xs text-muted-foreground">
              またはランキングページから議員を選択できます
            </p>
            <Button variant="outline" size="sm" className="mt-2" asChild>
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
    const prev = m.scores.length > 1 ? m.scores[1] : null;
    return { member: m, score: latest, prevScore: prev };
  });

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <div className="mb-8">
        <div className="flex items-center justify-between mb-2">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-2xl font-bold text-foreground">議員比較</h1>
              <ShareButton
                title={`議員比較: ${members.map((m) => m.name).join(" vs ")} | GiinScore`}
              />
            </div>
            <p className="text-sm text-muted-foreground">
              {members.map((m) => m.name).join(" / ")} の活動スコアを比較
            </p>
          </div>
          <Button variant="outline" asChild>
            <Link href="/">戻る</Link>
          </Button>
        </div>

        {/* 議員追加/削除 */}
        <div className="flex flex-wrap items-center gap-2 mt-4">
          {memberScores.map((ms, idx) => (
            <Badge
              key={ms.member.id}
              variant="outline"
              className="flex items-center gap-1.5 py-1 px-2.5"
            >
              <span
                className="inline-block h-2 w-2 rounded-full"
                style={{ backgroundColor: COMPARE_COLORS[idx].stroke }}
              />
              <span className="text-sm">{ms.member.name}</span>
              <button
                type="button"
                className="ml-1 text-muted-foreground hover:text-foreground"
                onClick={() => removeMember(ms.member.id)}
                aria-label={`${ms.member.name}を削除`}
              >
                &times;
              </button>
            </Badge>
          ))}
          {ids.length < 4 && (
            <CompareSearchInput existingIds={ids} onAdd={addMember} />
          )}
        </div>
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
              question_quality: ms.score?.question_quality ?? 0,
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
                  {memberScores.map((ms) => {
                    const diff = ms.score && ms.prevScore ? ms.score.total - ms.prevScore.total : null;
                    return (
                      <td
                        key={ms.member.id}
                        className="p-3 text-center text-lg font-bold"
                      >
                        {ms.score ? ms.score.total.toFixed(1) : "-"}
                        {diff !== null && diff !== 0 && (
                          <span className={`ml-1 text-xs font-medium ${diff > 0 ? "text-emerald-600" : "text-red-500"}`}>
                            {diff > 0 ? "+" : ""}{diff.toFixed(1)}
                          </span>
                        )}
                      </td>
                    );
                  })}
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
                        const prevValue = ms.prevScore?.[axis] ?? null;
                        const diff = value !== null && prevValue !== null ? value - prevValue : null;
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
                            {diff !== null && Math.abs(diff) >= 1 && (
                              <span className={`ml-1 text-[10px] ${diff > 0 ? "text-emerald-500" : "text-red-400"}`}>
                                {diff > 0 ? "\u2191" : "\u2193"}{Math.abs(diff).toFixed(0)}
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

      {/* 5軸ビジュアル差分バー */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="text-base">軸別スコア比較</CardTitle>
        </CardHeader>
        <CardContent className="space-y-5">
          {(["total", ...SCORE_AXES] as ScoreAxis[]).map((axis) => {
            const label = axis === "total" ? "総合スコア" : AXIS_LABELS[axis];
            const values = memberScores.map((ms) => ms.score?.[axis] ?? 0);
            const maxVal = Math.max(...values, 1);
            return (
              <div key={axis}>
                <p className="text-sm font-medium mb-2">{label}</p>
                <div className="space-y-1.5">
                  {memberScores.map((ms, idx) => (
                    <div key={ms.member.id} className="flex items-center gap-2">
                      <span
                        className="inline-block h-2 w-2 rounded-full shrink-0"
                        style={{ backgroundColor: COMPARE_COLORS[idx].stroke }}
                      />
                      <span className="text-xs w-20 truncate text-muted-foreground">{ms.member.name}</span>
                      <div className="flex-1">
                        <ScoreBar value={ms.score?.[axis] ?? 0} maxInGroup={maxVal} color={AXIS_BAR_COLORS[axis] ?? "bg-blue-500"} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </CardContent>
      </Card>

      {/* 勝敗サマリー (2名時) */}
      {memberScores.length === 2 && memberScores.every((ms) => ms.score) && (() => {
        const [a, b] = memberScores;
        const axes = [...SCORE_AXES, "total" as const];
        const aWins = axes.filter((ax) => (a.score?.[ax] ?? 0) > (b.score?.[ax] ?? 0)).length;
        const bWins = axes.filter((ax) => (b.score?.[ax] ?? 0) > (a.score?.[ax] ?? 0)).length;
        const draws = axes.length - aWins - bWins;
        return (
          <Card className="mb-6">
            <CardContent className="py-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="inline-block h-3 w-3 rounded-full" style={{ backgroundColor: COMPARE_COLORS[0].stroke }} />
                  <span className="text-sm font-medium">{a.member.name}</span>
                  <span className="text-xl font-bold text-blue-600">{aWins}</span>
                </div>
                <div className="text-center">
                  <span className="text-xs text-muted-foreground">引分</span>
                  <p className="text-lg font-bold text-muted-foreground">{draws}</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xl font-bold text-red-500">{bWins}</span>
                  <span className="text-sm font-medium">{b.member.name}</span>
                  <span className="inline-block h-3 w-3 rounded-full" style={{ backgroundColor: COMPARE_COLORS[1].stroke }} />
                </div>
              </div>
              <p className="text-xs text-muted-foreground text-center mt-1">6項目（総合 + 5軸）の優劣</p>
            </CardContent>
          </Card>
        );
      })()}

      {/* 最大差分ハイライト */}
      {memberScores.length >= 2 && memberScores.every((ms) => ms.score) && (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle className="text-base">注目すべき差</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {(["total", ...SCORE_AXES] as ScoreAxis[]).map((axis) => {
                const label = axis === "total" ? "総合" : AXIS_LABELS[axis];
                const entries = memberScores.map((ms, idx) => ({
                  name: ms.member.name,
                  value: ms.score?.[axis] ?? 0,
                  idx,
                }));
                const sorted = [...entries].sort((a, b) => b.value - a.value);
                const gap = sorted[0].value - sorted[sorted.length - 1].value;
                if (gap < 5) return null;
                return (
                  <div key={axis} className="rounded-lg border p-3">
                    <p className="text-xs text-muted-foreground mb-1">{label}</p>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1">
                        <span className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: COMPARE_COLORS[sorted[0].idx].stroke }} />
                        <span className="text-sm font-medium">{sorted[0].name}</span>
                        <span className="text-xs text-muted-foreground">{sorted[0].value.toFixed(1)}</span>
                      </div>
                      <span className={`text-xs font-bold ${gap > 30 ? "text-red-500" : "text-amber-500"}`}>
                        {gap > 30 ? "大差" : "差"} {gap.toFixed(0)}pt
                      </span>
                    </div>
                    <div className="flex items-center gap-1 mt-1">
                      <span className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: COMPARE_COLORS[sorted[sorted.length - 1].idx].stroke }} />
                      <span className="text-sm text-muted-foreground">{sorted[sorted.length - 1].name}</span>
                      <span className="text-xs text-muted-foreground">{sorted[sorted.length - 1].value.toFixed(1)}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
