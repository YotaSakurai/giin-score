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
import { useRanking, useStats, useSessions } from "@/lib/hooks";
import { ShareButton } from "@/components/ShareButton";
import { buildQuery } from "@/lib/api";
import { SCORE_DESCRIPTIONS, GRADE_DESCRIPTIONS } from "@/lib/constants";

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

function ScoreTooltip({ axis }: { axis: string }) {
  const desc = SCORE_DESCRIPTIONS[axis];
  if (!desc) return null;
  return (
    <span className="group relative inline-flex ml-1 cursor-help">
      <svg className="h-3.5 w-3.5 text-muted-foreground/60 hover:text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <circle cx="12" cy="12" r="10" />
        <path d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3" />
        <line x1="12" y1="17" x2="12.01" y2="17" />
      </svg>
      <span className="invisible group-hover:visible absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 rounded-lg bg-popover border border-border p-3 text-xs text-popover-foreground shadow-lg z-50">
        {desc.short}
      </span>
    </span>
  );
}

export default function HomeContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const chamber = searchParams.get("chamber") || "all";
  const sessionParam = searchParams.get("session") || "";
  const sortOrder = searchParams.get("sort") || "desc";
  const [districtSearch, setDistrictSearch] = useState("");

  const [compareIds, setCompareIds] = useState<number[]>(() => getStoredCompareIds());
  const [showGuide, setShowGuide] = useState(false);
  const [showOnboarding, setShowOnboarding] = useState(() => {
    if (typeof window === "undefined") return true;
    return !localStorage.getItem("giin-score-onboarding-dismissed");
  });

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
      router.push(`/compare?ids=${compareIds.join(",")}`);
    }
  }, [compareIds, router]);

  const chamberParam = chamber === "all" ? undefined : chamber;
  const sessionNumber = sessionParam ? Number(sessionParam) : undefined;

  const { data: sessions } = useSessions();

  const {
    data: rankingData,
    error: rankingError,
    isLoading: rankingLoading,
    mutate: mutateRanking,
  } = useRanking({ chamber: chamberParam, session_number: sessionNumber, sort_order: sortOrder, limit: 100 });

  const {
    data: stats,
    error: statsError,
    isLoading: statsLoading,
    mutate: mutateStats,
  } = useStats({ chamber: chamberParam, session_number: sessionNumber });

  const loading = rankingLoading || statsLoading;
  const error = rankingError || statsError;
  const ranking = rankingData?.items ?? [];

  const updateHomeParams = useCallback(
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
      router.push(qs ? `/?${qs}` : "/");
    },
    [router, searchParams],
  );

  const setChamber = useCallback(
    (value: string) => updateHomeParams({ chamber: value === "all" ? undefined : value }),
    [updateHomeParams],
  );

  const setSession = useCallback(
    (value: string) => updateHomeParams({ session: value === "latest" ? undefined : value }),
    [updateHomeParams],
  );

  const toggleSortOrder = useCallback(() => {
    updateHomeParams({ sort: sortOrder === "desc" ? "asc" : undefined });
  }, [updateHomeParams, sortOrder]);

  const handleRetry = useCallback(() => {
    mutateRanking();
    mutateStats();
  }, [mutateRanking, mutateStats]);

  const handleDistrictSearch = useCallback(() => {
    if (districtSearch.trim()) {
      router.push(`/members?district=${encodeURIComponent(districtSearch.trim())}&sort_by=total&sort_order=desc`);
    }
  }, [districtSearch, router]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      {/* 初心者向けオンボーディング */}
      {showOnboarding && (
        <Card className="mb-6 border-emerald-200 dark:border-emerald-800 bg-emerald-50/50 dark:bg-emerald-950/20">
          <CardContent className="p-6">
            <div className="flex items-start justify-between mb-3">
              <h2 className="text-lg font-bold text-foreground">GiinScoreの使い方</h2>
              <button
                onClick={() => {
                  setShowOnboarding(false);
                  localStorage.setItem("giin-score-onboarding-dismissed", "1");
                }}
                className="text-muted-foreground hover:text-foreground text-sm"
                aria-label="閉じる"
              >
                ✕
              </button>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="flex items-start gap-3">
                <span className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-emerald-500 text-white font-bold text-sm">1</span>
                <div>
                  <p className="text-sm font-medium">選挙区を入力</p>
                  <p className="text-xs text-muted-foreground">下の検索欄にお住まいの選挙区名を入力します</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <span className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-emerald-500 text-white font-bold text-sm">2</span>
                <div>
                  <p className="text-sm font-medium">スコアを比較</p>
                  <p className="text-xs text-muted-foreground">議員の5軸スコアを見て、活動量や質を確認します</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <span className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-emerald-500 text-white font-bold text-sm">3</span>
                <div>
                  <p className="text-sm font-medium">詳細を確認</p>
                  <p className="text-xs text-muted-foreground">議員をクリックして発言内容や投票記録を詳しく見ます</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 免責表示 */}
      <div className="mb-6 rounded-lg bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 px-4 py-3">
        <p className="text-xs text-amber-800 dark:text-amber-200">
          本スコアは国会の公開データに基づく活動量の可視化であり、政治家の能力・人格・政策の正しさを評価するものではありません。
        </p>
      </div>

      {/* 選挙区検索CTA */}
      <Card className="mb-8 border-blue-200 dark:border-blue-800 bg-blue-50/50 dark:bg-blue-950/20">
        <CardContent className="p-6">
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
            <div className="flex-1">
              <h2 className="text-lg font-bold text-foreground mb-1">あなたの選挙区の議員を調べる</h2>
              <p className="text-sm text-muted-foreground">選挙区名を入力すると、その地域の国会議員のスコアを確認できます</p>
            </div>
            <div className="flex gap-2 w-full sm:w-auto">
              <input
                type="text"
                placeholder="例: 東京1区、北海道"
                value={districtSearch}
                onChange={(e) => setDistrictSearch(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleDistrictSearch()}
                className="flex-1 sm:w-56 rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
              />
              <Button onClick={handleDistrictSearch} disabled={!districtSearch.trim()}>
                <svg className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <circle cx="11" cy="11" r="8" />
                  <path d="M21 21l-4.35-4.35" />
                </svg>
                検索
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* ヘッダー */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <h1 className="text-2xl font-bold text-foreground">
            {sortOrder === "asc" ? "議員活動ワーストランキング" : "議員活動ランキング"}
          </h1>
          <ShareButton
            title="議員活動ランキング | GiinScore - 国会議員の活動スコアを可視化"
          />
        </div>
        <p className="text-sm text-muted-foreground">
          {sortOrder === "asc"
            ? "国会活動が低い議員のランキング — スコアが低い議員ほど議会での活動が少ないことを示します"
            : "国会における議員の活動スコアランキング"}
        </p>
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
              <p className="text-xs text-muted-foreground">平均スコア<ScoreTooltip axis="total" /></p>
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

      {/* グレード分布 */}
      {stats && stats.distribution.length > 0 && (
        <Card className="mb-8">
          <CardContent className="p-4">
            <h3 className="text-sm font-semibold mb-3">グレード分布</h3>
            <div className="flex items-end gap-2 h-24">
              {(["A", "B", "C", "D", "F"] as const).map((grade) => {
                const dist = stats.distribution.find((d) => d.grade === grade);
                const count = dist?.count ?? 0;
                const pct = dist?.percentage ?? 0;
                const maxPct = Math.max(...stats.distribution.map((d) => d.percentage), 1);
                const barHeight = (pct / maxPct) * 100;
                const gradeColor = GRADE_COLORS[grade] || "bg-gray-300";
                return (
                  <Link
                    key={grade}
                    href={`/members?grade=${grade}&sort_by=total&sort_order=desc`}
                    className="flex-1 flex flex-col items-center gap-1 group cursor-pointer"
                  >
                    <span className="text-xs text-muted-foreground">{count}名</span>
                    <div className="w-full flex justify-center">
                      <div
                        className={`w-full max-w-12 rounded-t ${gradeColor} group-hover:opacity-80 transition-opacity`}
                        style={{ height: `${Math.max(barHeight, 4)}%` }}
                      />
                    </div>
                    <span className="text-xs font-medium">{grade}</span>
                    <span className="text-xs text-muted-foreground">{pct}%</span>
                  </Link>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* TOP3 ハイライト */}
      {sortOrder === "desc" && ranking.length >= 3 && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
          {ranking.slice(0, 3).map((entry, idx) => {
            const colors = ["border-yellow-400 bg-yellow-50 dark:bg-yellow-950/30", "border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-800/50", "border-amber-600 bg-amber-50 dark:bg-amber-950/30"];
            const medals = ["\u{1F947}", "\u{1F948}", "\u{1F949}"];
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
      <div className="flex items-center gap-4 mb-6 flex-wrap">
        <Select value={chamber} onValueChange={setChamber}>
          <SelectTrigger className="w-40" aria-label="院を選択">
            <SelectValue placeholder="院を選択" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全て</SelectItem>
            <SelectItem value="representatives">衆議院</SelectItem>
            <SelectItem value="councillors">参議院</SelectItem>
          </SelectContent>
        </Select>
        {sessions && sessions.length > 0 && (
          <Select value={sessionParam || "latest"} onValueChange={setSession}>
            <SelectTrigger className="w-48" aria-label="会期を選択">
              <SelectValue placeholder="会期を選択" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="latest">最新会期</SelectItem>
              {sessions.map((s) => (
                <SelectItem key={s.id} value={String(s.session_number)}>
                  第{s.session_number}回 {s.kind}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
        <Button
          variant={sortOrder === "asc" ? "default" : "outline"}
          size="sm"
          onClick={toggleSortOrder}
          aria-label={sortOrder === "asc" ? "高スコア順に切替" : "低スコア順に切替"}
        >
          {sortOrder === "asc" ? (
            <>
              <svg className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 4h13M3 8h9m-9 4h6m4 0l4-4m0 0l4 4m-4-4v12" />
              </svg>
              低スコア順
            </>
          ) : (
            <>
              <svg className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 4h13M3 8h9m-9 4h9m5-4v12m0 0l-4-4m4 4l4-4" />
              </svg>
              高スコア順
            </>
          )}
        </Button>
        <Button variant="outline" size="sm" onClick={() => setShowGuide(!showGuide)}>
          <svg className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <circle cx="12" cy="12" r="10" />
            <path d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3" />
            <line x1="12" y1="17" x2="12.01" y2="17" />
          </svg>
          スコアの見方
        </Button>
        <a
          href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"}/scores/export/csv${buildQuery({ chamber: chamberParam, session_number: sessionNumber })}`}
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

      {/* スコアガイド */}
      {showGuide && (
        <Card className="mb-6 bg-slate-50 dark:bg-slate-900/50">
          <CardHeader>
            <CardTitle className="text-base">スコアの見方ガイド</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <h3 className="text-sm font-semibold mb-2">グレード</h3>
              <div className="grid grid-cols-1 sm:grid-cols-5 gap-2">
                {(["A", "B", "C", "D", "F"] as const).map((g) => (
                  <div key={g} className="flex items-center gap-2">
                    <span className={`inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-white text-xs font-bold ${GRADE_COLORS[g]}`}>
                      {g}
                    </span>
                    <span className="text-xs text-muted-foreground">{GRADE_DESCRIPTIONS[g]}</span>
                  </div>
                ))}
              </div>
            </div>
            <div>
              <h3 className="text-sm font-semibold mb-2">スコアの5軸</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {(["legislative_activity", "voting_behavior", "policy_influence", "transparency", "question_quality"] as const).map((axis) => {
                  const labels: Record<string, string> = {
                    legislative_activity: "立法活動",
                    voting_behavior: "投票行動",
                    policy_influence: "政策影響力",
                    transparency: "透明性",
                    question_quality: "質問品質",
                  };
                  return (
                    <div key={axis} className="rounded-lg border p-3 bg-background">
                      <p className="text-sm font-medium mb-1">{labels[axis]}</p>
                      <p className="text-xs text-muted-foreground">{SCORE_DESCRIPTIONS[axis].short}</p>
                    </div>
                  );
                })}
              </div>
            </div>
            <p className="text-xs text-muted-foreground">
              スコアは同じ院・同じ役職の議員同士でパーセンタイルランク（0-100）に変換しています。50が平均的な位置です。
            </p>
          </CardContent>
        </Card>
      )}

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
            <CardTitle className="text-base">
              {sortOrder === "asc" ? "WORST" : "TOP"} {ranking.length}
            </CardTitle>
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
                    <th scope="col" className="p-3 text-right">スコア<ScoreTooltip axis="total" /></th>
                    <th scope="col" className="p-3 hidden lg:table-cell text-right">立法<ScoreTooltip axis="legislative_activity" /></th>
                    <th scope="col" className="p-3 hidden lg:table-cell text-right">投票<ScoreTooltip axis="voting_behavior" /></th>
                    <th scope="col" className="p-3 hidden lg:table-cell text-right">影響<ScoreTooltip axis="policy_influence" /></th>
                    <th scope="col" className="p-3 hidden lg:table-cell text-right">透明<ScoreTooltip axis="transparency" /></th>
                    <th scope="col" className="p-3 hidden lg:table-cell text-right">質問<ScoreTooltip axis="question_quality" /></th>
                  </tr>
                </thead>
                <tbody>
                  {ranking.map((entry) => {
                    const gradeColor = GRADE_COLORS[entry.score.grade] || "bg-gray-300";
                    const isSelected = compareIds.includes(entry.member.id);
                    const isDisabled = !isSelected && compareIds.length >= MAX_COMPARE;
                    return (
                      <tr
                        key={entry.member.id}
                        className={`border-b hover:bg-muted/50 transition-colors ${
                          entry.score.grade === "F" ? "bg-red-50/50 dark:bg-red-950/10" :
                          entry.score.grade === "D" ? "bg-orange-50/30 dark:bg-orange-950/10" : ""
                        }`}
                      >
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
                        <td className="p-3 hidden lg:table-cell text-right text-xs text-muted-foreground">{entry.score.question_quality.toFixed(0)}</td>
                      </tr>
                    );
                  })}
                  {ranking.length === 0 && (
                    <tr>
                      <td colSpan={12} className="p-8 text-center text-sm text-muted-foreground">
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
