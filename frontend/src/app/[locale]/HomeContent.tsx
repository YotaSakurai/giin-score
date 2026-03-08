"use client";

import { useCallback, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Link } from "@/i18n/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { LoadingSpinner } from "@/components/ui/loading";
import { ErrorMessage } from "@/components/ui/error";
import { CHAMBER_LABELS, GRADE_COLORS } from "@/lib/types";
import { useRanking, useStats } from "@/lib/hooks";
import { ShareButton } from "@/components/ShareButton";
import { buildQuery } from "@/lib/api";

const COMPARE_STORAGE_KEY = "giin-score-compare-ids";
const MAX_COMPARE = 4;

function getStoredCompareIds(): number[] {
  if (typeof window === "undefined") return [];
  try {
    const stored = localStorage.getItem(COMPARE_STORAGE_KEY);
    if (!stored) return [];
    return JSON.parse(stored) as number[];
  } catch {
    return [];
  }
}

function setStoredCompareIds(ids: number[]) {
  if (typeof window === "undefined") return;
  localStorage.setItem(COMPARE_STORAGE_KEY, JSON.stringify(ids));
}

export default function HomeContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const chamber = searchParams.get("chamber") || "all";

  const [compareIds, setCompareIds] = useState<number[]>(() => getStoredCompareIds());

  const toggleCompare = useCallback((memberId: number) => {
    setCompareIds((prev) => {
      let next: number[];
      if (prev.includes(memberId)) {
        next = prev.filter((id) => id !== memberId);
      } else {
        if (prev.length >= MAX_COMPARE) return prev;
        next = [...prev, memberId];
      }
      setStoredCompareIds(next);
      return next;
    });
  }, []);

  const clearCompare = useCallback(() => {
    setCompareIds([]);
    setStoredCompareIds([]);
  }, []);

  const goToCompare = useCallback(() => {
    if (compareIds.length >= 2) {
      // 遷移後にlocalStorageをクリアしない（比較ページでも参照可能にするため）
      router.push(`/compare?ids=${compareIds.join(",")}`);
    }
  }, [compareIds, router]);

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
      <div className="mb-6 rounded-lg bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 px-4 py-3">
        <p className="text-xs text-amber-800 dark:text-amber-200">
          本スコアは国会の公開データに基づく活動量の可視化であり、政治家の能力・人格・政策の正しさを評価するものではありません。
        </p>
      </div>

      {/* ヘッダー */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <h1 className="text-2xl font-bold text-foreground">議員活動ランキング</h1>
          <ShareButton
            title="議員活動ランキング | GiinScore - 国会議員の活動スコアを可視化"
          />
        </div>
        <p className="text-sm text-muted-foreground">国会における議員の活動スコアランキング</p>
      </div>

      {/* 統計概要 */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
          <Card>
            <CardContent className="p-4 text-center">
              <p className="text-2xl font-bold text-foreground">{stats.total_members}</p>
              <p className="text-xs text-muted-foreground">対象議員数</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <p className="text-2xl font-bold text-blue-600">{stats.average_score.toFixed(1)}</p>
              <p className="text-xs text-muted-foreground">平均スコア</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <p className="text-2xl font-bold text-foreground">{stats.median_score.toFixed(1)}</p>
              <p className="text-xs text-muted-foreground">中央値</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <p className="text-2xl font-bold text-emerald-600">{stats.max_score.toFixed(1)}</p>
              <p className="text-xs text-muted-foreground">最高スコア</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <p className="text-2xl font-bold text-red-500">{stats.min_score.toFixed(1)}</p>
              <p className="text-xs text-muted-foreground">最低スコア</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* TOP3 ハイライト */}
      {ranking.length >= 3 && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
          {ranking.slice(0, 3).map((entry, idx) => {
            const colors = ["border-yellow-400 bg-yellow-50 dark:bg-yellow-950/30", "border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-800/50", "border-amber-600 bg-amber-50 dark:bg-amber-950/30"];
            const medals = ["🥇", "🥈", "🥉"];
            const gradeColor = GRADE_COLORS[entry.score.grade] || "bg-gray-300";
            return (
              <Card key={entry.member.id} className={`border-2 ${colors[idx]}`}>
                <CardContent className="p-4">
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">{medals[idx]}</span>
                    <span className={`inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-white text-sm font-bold ${gradeColor}`}>
                      {entry.score.grade}
                    </span>
                    <div className="flex-1 min-w-0">
                      <Link href={`/members/${entry.member.id}`} className="text-sm font-bold text-blue-600 hover:underline truncate block">
                        {entry.member.name}
                      </Link>
                      <p className="text-xs text-muted-foreground truncate">{entry.member.party ?? "無所属"}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-xl font-bold">{entry.score.total.toFixed(1)}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
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
        <a
          href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"}/scores/export/csv${buildQuery({ chamber: chamberParam })}`}
          download
        >
          <Button variant="outline" size="sm">
            <svg className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            CSV
          </Button>
        </a>
      </div>

      {/* コンテンツ */}
      {loading ? (
        <LoadingSpinner />
      ) : error ? (
        <ErrorMessage message={error instanceof Error ? error.message : "データの取得に失敗しました"} onRetry={handleRetry} />
      ) : (
        <>
        {/* モバイルカードビュー */}
        <div className="sm:hidden space-y-3">
          {ranking.map((entry) => {
            const gradeColor = GRADE_COLORS[entry.score.grade] || "bg-gray-300";
            const isSelected = compareIds.includes(entry.member.id);
            const isDisabled = !isSelected && compareIds.length >= MAX_COMPARE;
            return (
              <Card key={entry.member.id} className="relative">
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
                      <div className="flex items-center gap-2 text-xs text-muted-foreground mt-0.5">
                        <span>{entry.member.party ?? "無所属"}</span>
                        <span>{CHAMBER_LABELS[entry.member.chamber]}</span>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-lg font-bold">{entry.score.total.toFixed(1)}</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => toggleCompare(entry.member.id)}
                      disabled={isDisabled}
                      className={`inline-flex h-6 w-6 shrink-0 items-center justify-center rounded border transition-colors ${
                        isSelected
                          ? "bg-blue-600 border-blue-600 text-white"
                          : isDisabled
                            ? "border-muted bg-muted/50 cursor-not-allowed"
                            : "border-border"
                      }`}
                      aria-label={`${entry.member.name}を比較に${isSelected ? "解除" : "追加"}`}
                    >
                      {isSelected && (
                        <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                        </svg>
                      )}
                    </button>
                  </div>
                </CardContent>
              </Card>
            );
          })}
          {ranking.length === 0 && (
            <p className="p-8 text-center text-sm text-muted-foreground">
              スコアデータがまだありません
            </p>
          )}
        </div>

        {/* デスクトップテーブルビュー */}
        <Card className="hidden sm:block">
          <CardHeader>
            <CardTitle className="text-base">TOP {ranking.length}</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b bg-muted/50 text-left text-xs text-muted-foreground">
                    <th scope="col" className="p-3 w-10 text-center">比較</th>
                    <th scope="col" className="p-3 w-12">#</th>
                    <th scope="col" className="p-3">議員名</th>
                    <th scope="col" className="p-3">政党</th>
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
                    const isSelected = compareIds.includes(entry.member.id);
                    const isDisabled = !isSelected && compareIds.length >= MAX_COMPARE;
                    return (
                      <tr key={entry.member.id} className="border-b hover:bg-muted/50 transition-colors">
                        <td className="p-3 text-center">
                          <button
                            type="button"
                            onClick={() => toggleCompare(entry.member.id)}
                            disabled={isDisabled}
                            className={`inline-flex h-5 w-5 items-center justify-center rounded border transition-colors ${
                              isSelected
                                ? "bg-blue-600 border-blue-600 text-white"
                                : isDisabled
                                  ? "border-muted bg-muted/50 cursor-not-allowed"
                                  : "border-slate-300 hover:border-blue-400"
                            }`}
                            aria-label={`${entry.member.name}を比較に${isSelected ? "解除" : "追加"}`}
                          >
                            {isSelected && (
                              <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                              </svg>
                            )}
                          </button>
                        </td>
                        <td className="p-3 text-sm font-medium text-muted-foreground">{entry.rank}</td>
                        <td className="p-3">
                          <Link href={`/members/${entry.member.id}`} className="text-sm font-medium text-blue-600 hover:underline">
                            {entry.member.name}
                          </Link>
                        </td>
                        <td className="p-3 text-sm text-muted-foreground">{entry.member.party ?? "無所属"}</td>
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
                        <td className="p-3 hidden lg:table-cell text-right text-xs text-muted-foreground">{entry.score.legislative_activity.toFixed(0)}</td>
                        <td className="p-3 hidden lg:table-cell text-right text-xs text-muted-foreground">{entry.score.voting_behavior.toFixed(0)}</td>
                        <td className="p-3 hidden lg:table-cell text-right text-xs text-muted-foreground">{entry.score.policy_influence.toFixed(0)}</td>
                        <td className="p-3 hidden lg:table-cell text-right text-xs text-muted-foreground">{entry.score.transparency.toFixed(0)}</td>
                      </tr>
                    );
                  })}
                  {ranking.length === 0 && (
                    <tr>
                      <td colSpan={11} className="p-8 text-center text-sm text-muted-foreground">
                        スコアデータがまだありません
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

      {/* フローティング比較ボタン */}
      {compareIds.length >= 1 && (
        <div className="fixed bottom-6 right-6 z-50 flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={clearCompare}
            className="bg-background shadow-lg"
          >
            クリア
          </Button>
          <Button
            onClick={goToCompare}
            disabled={compareIds.length < 2}
            className="shadow-lg"
            size="lg"
          >
            <svg
              className="h-4 w-4 mr-1"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
              />
            </svg>
            比較する ({compareIds.length}/{MAX_COMPARE})
          </Button>
        </div>
      )}
    </div>
  );
}
