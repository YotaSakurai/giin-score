"use client";

import { useCallback } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { LoadingSpinner } from "@/components/ui/loading";
import { ErrorMessage } from "@/components/ui/error";
import { CHAMBER_LABELS, GRADE_COLORS } from "@/lib/types";
import { useRanking, useStats } from "@/lib/hooks";

export default function HomeContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const chamber = searchParams.get("chamber") || "all";

  const chamberParam = chamber === "all" ? undefined : chamber;

  const {
    data: rankingData,
    error: rankingError,
    isLoading: rankingLoading,
    mutate: mutateRanking,
  } = useRanking({ chamber: chamberParam, limit: 100 });

  const {
    data: stats,
    error: statsError,
    isLoading: statsLoading,
    mutate: mutateStats,
  } = useStats({ chamber: chamberParam });

  const loading = rankingLoading || statsLoading;
  const error = rankingError || statsError;
  const ranking = rankingData?.items ?? [];

  const setChamber = useCallback(
    (value: string) => {
      const params = new URLSearchParams(searchParams.toString());
      if (value === "all") {
        params.delete("chamber");
      } else {
        params.set("chamber", value);
      }
      const qs = params.toString();
      router.push(qs ? `/?${qs}` : "/");
    },
    [router, searchParams],
  );

  const handleRetry = useCallback(() => {
    mutateRanking();
    mutateStats();
  }, [mutateRanking, mutateStats]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      {/* 免責表示 */}
      <div className="mb-6 rounded-lg bg-amber-50 border border-amber-200 px-4 py-3">
        <p className="text-xs text-amber-800">
          本スコアは国会の公開データに基づく活動量の可視化であり、政治家の能力・人格・政策の正しさを評価するものではありません。
        </p>
      </div>

      {/* ヘッダー */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-800 mb-2">議員活動ランキング</h1>
        <p className="text-sm text-slate-500">国会における議員の活動スコアランキング</p>
      </div>

      {/* 統計概要 */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
          <Card>
            <CardContent className="p-4 text-center">
              <p className="text-2xl font-bold text-slate-800">{stats.total_members}</p>
              <p className="text-xs text-slate-500">対象議員数</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <p className="text-2xl font-bold text-blue-600">{stats.average_score.toFixed(1)}</p>
              <p className="text-xs text-slate-500">平均スコア</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <p className="text-2xl font-bold text-slate-700">{stats.median_score.toFixed(1)}</p>
              <p className="text-xs text-slate-500">中央値</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <p className="text-2xl font-bold text-emerald-600">{stats.max_score.toFixed(1)}</p>
              <p className="text-xs text-slate-500">最高スコア</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <p className="text-2xl font-bold text-red-500">{stats.min_score.toFixed(1)}</p>
              <p className="text-xs text-slate-500">最低スコア</p>
            </CardContent>
          </Card>
        </div>
      )}

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

      {/* コンテンツ */}
      {loading ? (
        <LoadingSpinner />
      ) : error ? (
        <ErrorMessage message={error instanceof Error ? error.message : "データの取得に失敗しました"} onRetry={handleRetry} />
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">TOP {ranking.length}</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b bg-slate-50 text-left text-xs text-slate-500">
                    <th scope="col" className="p-3 w-12">#</th>
                    <th scope="col" className="p-3">議員名</th>
                    <th scope="col" className="p-3 hidden sm:table-cell">政党</th>
                    <th scope="col" className="p-3 hidden md:table-cell">院</th>
                    <th scope="col" className="p-3 text-center">グレード</th>
                    <th scope="col" className="p-3 text-right">スコア</th>
                    <th scope="col" className="p-3 hidden lg:table-cell text-right">立法</th>
                    <th scope="col" className="p-3 hidden lg:table-cell text-right">投票</th>
                    <th scope="col" className="p-3 hidden lg:table-cell text-right">影響</th>
                    <th scope="col" className="p-3 hidden lg:table-cell text-right">透明</th>
                  </tr>
                </thead>
                <tbody>
                  {ranking.map((entry) => {
                    const gradeColor = GRADE_COLORS[entry.score.grade] || "bg-gray-300";
                    return (
                      <tr key={entry.member.id} className="border-b hover:bg-slate-50 transition-colors">
                        <td className="p-3 text-sm font-medium text-slate-500">{entry.rank}</td>
                        <td className="p-3">
                          <Link href={`/members/${entry.member.id}`} className="text-sm font-medium text-blue-600 hover:underline">
                            {entry.member.name}
                          </Link>
                        </td>
                        <td className="p-3 hidden sm:table-cell text-sm text-slate-600">{entry.member.party ?? "無所属"}</td>
                        <td className="p-3 hidden md:table-cell">
                          <Badge variant="outline" className="text-xs">
                            {CHAMBER_LABELS[entry.member.chamber]}
                          </Badge>
                        </td>
                        <td className="p-3 text-center">
                          <span className={`inline-flex h-7 w-7 items-center justify-center rounded-full text-white text-xs font-bold ${gradeColor}`}>
                            {entry.score.grade}
                          </span>
                        </td>
                        <td className="p-3 text-right text-sm font-bold">{entry.score.total.toFixed(1)}</td>
                        <td className="p-3 hidden lg:table-cell text-right text-xs text-slate-600">{entry.score.legislative_activity.toFixed(0)}</td>
                        <td className="p-3 hidden lg:table-cell text-right text-xs text-slate-600">{entry.score.voting_behavior.toFixed(0)}</td>
                        <td className="p-3 hidden lg:table-cell text-right text-xs text-slate-600">{entry.score.policy_influence.toFixed(0)}</td>
                        <td className="p-3 hidden lg:table-cell text-right text-xs text-slate-600">{entry.score.transparency.toFixed(0)}</td>
                      </tr>
                    );
                  })}
                  {ranking.length === 0 && (
                    <tr>
                      <td colSpan={10} className="p-8 text-center text-sm text-slate-500">
                        スコアデータがまだありません
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
