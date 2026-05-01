"use client";

import { useCallback, useMemo, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { LoadingSpinner } from "@/components/ui/loading";
import { ErrorMessage } from "@/components/ui/error";
import { AXIS_LABELS, GRADE_COLORS } from "@/lib/types";
import type { PartyTrendResponse } from "@/lib/types";
import { usePartyStats, usePartyTrend } from "@/lib/hooks";
import { ShareButton } from "@/components/ShareButton";
import { PartyBarChart } from "@/components/score/PartyBarChart";
import dynamic from "next/dynamic";

const CompareRadarChart = dynamic(
  () => import("@/components/score/CompareRadarChart").then(m => ({ default: m.CompareRadarChart })),
  { loading: () => <LoadingSpinner /> },
);

const PartyTrendChart = dynamic(
  () => import("@/components/score/PartyTrendChart").then(m => ({ default: m.PartyTrendChart })),
  { loading: () => <LoadingSpinner /> },
);

const PARTY_COLORS = [
  { stroke: "#3b82f6", fill: "#3b82f6" },
  { stroke: "#ef4444", fill: "#ef4444" },
  { stroke: "#10b981", fill: "#10b981" },
  { stroke: "#f59e0b", fill: "#f59e0b" },
  { stroke: "#8b5cf6", fill: "#8b5cf6" },
];

type SortKey =
  | "average_score"
  | "member_count"
  | "average_legislative_activity"
  | "average_voting_behavior"
  | "average_policy_influence"
  | "average_transparency"
  | "average_question_quality";

const SORT_COLUMNS: { key: SortKey; label: string; className?: string }[] = [
  { key: "member_count", label: "議員数" },
  { key: "average_score", label: "平均スコア" },
  { key: "average_legislative_activity", label: AXIS_LABELS.legislative_activity, className: "hidden lg:table-cell" },
  { key: "average_voting_behavior", label: AXIS_LABELS.voting_behavior, className: "hidden lg:table-cell" },
  { key: "average_policy_influence", label: AXIS_LABELS.policy_influence, className: "hidden lg:table-cell" },
  { key: "average_transparency", label: AXIS_LABELS.transparency, className: "hidden lg:table-cell" },
  { key: "average_question_quality", label: AXIS_LABELS.question_quality, className: "hidden lg:table-cell" },
];

const GRADES = ["A", "B", "C", "D", "F"] as const;

export default function PartyStatsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const chamber = searchParams.get("chamber") || "all";
  const [sortKey, setSortKey] = useState<SortKey>("average_score");
  const [sortAsc, setSortAsc] = useState(false);

  const chamberParam = chamber === "all" ? undefined : chamber;

  const {
    data,
    error,
    isLoading,
    mutate,
  } = usePartyStats({ chamber: chamberParam });

  const { data: trendData } = usePartyTrend({ chamber: chamberParam });

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

  const handleSort = useCallback(
    (key: SortKey) => {
      if (sortKey === key) {
        setSortAsc((prev) => !prev);
      } else {
        setSortKey(key);
        setSortAsc(false);
      }
    },
    [sortKey],
  );

  const sortedItems = useMemo(() => {
    const items = [...(data?.items ?? [])];
    items.sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      return sortAsc ? av - bv : bv - av;
    });
    return items;
  }, [data?.items, sortKey, sortAsc]);

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
              <PartyBarChart items={sortedItems} />
            </CardContent>
          </Card>

          {/* 政党レーダーチャート (TOP5) */}
          {sortedItems.length >= 2 && (
            <Card className="mb-6">
              <CardHeader>
                <CardTitle className="text-base">上位政党の5軸比較</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-4 mb-4 justify-center">
                  {sortedItems.slice(0, 5).map((entry, idx) => (
                    <div key={entry.party} className="flex items-center gap-2">
                      <span className="inline-block h-3 w-3 rounded-full" style={{ backgroundColor: PARTY_COLORS[idx].stroke }} />
                      <span className="text-sm text-foreground/80">{entry.party}</span>
                    </div>
                  ))}
                </div>
                <CompareRadarChart
                  members={sortedItems.slice(0, 5).map((entry, idx) => ({
                    name: entry.party,
                    legislative_activity: entry.average_legislative_activity,
                    voting_behavior: entry.average_voting_behavior,
                    policy_influence: entry.average_policy_influence,
                    transparency: entry.average_transparency,
                    question_quality: entry.average_question_quality,
                    color: PARTY_COLORS[idx],
                  }))}
                />
              </CardContent>
            </Card>
          )}

          {/* 政党スコア推移チャート */}
          {trendData && trendData.sessions.length >= 2 && sortedItems.length > 0 && (
            <Card className="mb-6">
              <CardHeader>
                <CardTitle className="text-base">政党平均スコア推移</CardTitle>
              </CardHeader>
              <CardContent>
                <PartyTrendChart
                  trendData={trendData}
                  topParties={sortedItems.slice(0, 5).map((e) => e.party)}
                  colors={PARTY_COLORS}
                />
              </CardContent>
            </Card>
          )}

          {/* グレード分布スタックドバー */}
          {sortedItems.length > 0 && (
            <Card className="mb-6">
              <CardHeader>
                <CardTitle className="text-base">政党別グレード分布</CardTitle>
                <p className="text-xs text-muted-foreground">各政党のグレード構成比（%）</p>
              </CardHeader>
              <CardContent className="space-y-3">
                {sortedItems.map((entry) => {
                  const total = entry.member_count;
                  if (total === 0) return null;
                  return (
                    <div key={entry.party}>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-medium w-28 truncate">{entry.party}</span>
                        <span className="text-xs text-muted-foreground">{total}名</span>
                      </div>
                      <div className="flex h-5 rounded-full overflow-hidden">
                        {GRADES.map((grade) => {
                          const count = entry.grade_distribution[grade] ?? 0;
                          if (count === 0) return null;
                          const pct = (count / total) * 100;
                          return (
                            <div
                              key={grade}
                              className={`${GRADE_COLORS[grade]} flex items-center justify-center text-[9px] font-bold text-white`}
                              style={{ width: `${pct}%` }}
                              title={`${grade}: ${count}名 (${pct.toFixed(0)}%)`}
                            >
                              {pct >= 8 ? `${grade}${count}` : ""}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
                <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
                  {GRADES.map((g) => (
                    <span key={g} className="flex items-center gap-1">
                      <span className={`h-2.5 w-2.5 rounded-sm ${GRADE_COLORS[g]}`} />
                      {g}
                    </span>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

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
                      <th scope="col" className="p-3 hidden sm:table-cell">グレード分布</th>
                      {SORT_COLUMNS.map((col) => (
                        <SortableHeader
                          key={col.key}
                          sortKey={col.key}
                          label={col.label}
                          currentSort={sortKey}
                          sortAsc={sortAsc}
                          onClick={handleSort}
                          className={col.className}
                        />
                      ))}
                      <th scope="col" className="p-3 text-right hidden sm:table-cell">中央値</th>
                      <th scope="col" className="p-3 text-right hidden md:table-cell">最高</th>
                      <th scope="col" className="p-3 text-right hidden md:table-cell">最低</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedItems.map((entry, idx) => {
                      const lowGradeCount = (entry.grade_distribution["D"] ?? 0) + (entry.grade_distribution["F"] ?? 0);
                      const lowGradeRate = entry.member_count > 0 ? (lowGradeCount / entry.member_count * 100) : 0;
                      return (
                      <tr key={entry.party} className={`border-b hover:bg-muted/50 transition-colors ${lowGradeRate > 50 ? "bg-red-50/30 dark:bg-red-950/10" : ""}`}>
                        <td className="p-3 text-sm font-medium text-muted-foreground">{idx + 1}</td>
                        <td className="p-3 text-sm font-medium text-foreground">
                          <Link
                            href={`/members?party=${encodeURIComponent(entry.party)}`}
                            className="text-primary hover:underline"
                          >
                            {entry.party}
                          </Link>
                          {lowGradeRate > 50 && (
                            <span className="ml-1 text-xs text-red-500" title={`D/Fグレード議員が${lowGradeRate.toFixed(0)}%`}>
                              (低活動{lowGradeRate.toFixed(0)}%)
                            </span>
                          )}
                        </td>
                        <td className="p-3 hidden sm:table-cell">
                          <GradeBadges distribution={entry.grade_distribution} />
                        </td>
                        <td className="p-3 text-right text-sm text-muted-foreground">{entry.member_count}</td>
                        <td className="p-3 text-right text-sm font-bold">{entry.average_score.toFixed(1)}</td>
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
                        <td className="p-3 text-right text-sm text-muted-foreground hidden sm:table-cell">
                          {entry.median_score.toFixed(1)}
                        </td>
                        <td className="p-3 text-right text-sm text-emerald-600 hidden md:table-cell">
                          {entry.max_score.toFixed(1)}
                        </td>
                        <td className="p-3 text-right text-sm text-red-500 hidden md:table-cell">
                          {entry.min_score.toFixed(1)}
                        </td>
                      </tr>
                      );
                    })}
                    {sortedItems.length === 0 && (
                      <tr>
                        <td colSpan={14} className="p-8 text-center text-sm text-muted-foreground">
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

function SortableHeader({
  sortKey,
  label,
  currentSort,
  sortAsc,
  onClick,
  className = "",
}: {
  sortKey: SortKey;
  label: string;
  currentSort: SortKey;
  sortAsc: boolean;
  onClick: (key: SortKey) => void;
  className?: string;
}) {
  const isActive = currentSort === sortKey;
  const ariaSort = isActive ? (sortAsc ? "ascending" : "descending") : undefined;
  return (
    <th
      scope="col"
      className={`p-3 text-right cursor-pointer select-none hover:text-foreground ${className}`}
      onClick={() => onClick(sortKey)}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onClick(sortKey); } }}
      tabIndex={0}
      role="columnheader"
      aria-sort={ariaSort}
      aria-label={`${label}でソート`}
    >
      {label}
      {isActive && (
        <span className="ml-0.5" aria-hidden="true">{sortAsc ? "▲" : "▼"}</span>
      )}
    </th>
  );
}

function GradeBadges({ distribution }: { distribution: Record<string, number> }) {
  return (
    <div className="flex gap-1">
      {GRADES.map((grade) => {
        const count = distribution[grade] ?? 0;
        if (count === 0) return null;
        return (
          <span
            key={grade}
            className={`inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 text-[10px] font-medium text-white ${GRADE_COLORS[grade]}`}
          >
            {grade}{count}
          </span>
        );
      })}
    </div>
  );
}
