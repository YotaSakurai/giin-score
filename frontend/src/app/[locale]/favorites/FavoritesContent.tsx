"use client";

import { useCallback, useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import { Link } from "@/i18n/navigation";
import useSWR from "swr";
import { swrFetcher } from "@/lib/api";
import type { MemberDetail } from "@/lib/types";
import { CHAMBER_LABELS, GRADE_COLORS } from "@/lib/types";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { LoadingSpinner } from "@/components/ui/loading";
import { getFavorites, setFavorites } from "@/lib/favorites";
import { FavoriteButton } from "@/components/FavoriteButton";

/** 複数IDの議員データを一括取得するカスタムフック */
function useFavoriteMembers(ids: number[]) {
  // SWRキーをIDリストから安定的に生成
  const key = ids.length > 0 ? `/favorites-batch?ids=${ids.join(",")}` : null;

  const { data, isLoading } = useSWR<MemberDetail[]>(
    key,
    async () => {
      const results = await Promise.all(
        ids.map((id) => swrFetcher<MemberDetail>(`/members/${id}`).catch(() => null)),
      );
      return results.filter((r): r is MemberDetail => r !== null);
    },
    { revalidateOnFocus: false },
  );

  return { members: data ?? [], isLoading };
}

export default function FavoritesContent() {
  const router = useRouter();
  const [favoriteIds, setFavoriteIds] = useState<number[]>(() => getFavorites());
  const [compareSelection, setCompareSelection] = useState<number[]>([]);

  const ids = useMemo(() => favoriteIds.slice(0, 20), [favoriteIds]);
  const { members, isLoading } = useFavoriteMembers(ids);

  const handleRemove = useCallback((memberId: number) => {
    const next = favoriteIds.filter((id) => id !== memberId);
    setFavoriteIds(next);
    setFavorites(next);
  }, [favoriteIds]);

  const handleClearAll = useCallback(() => {
    setFavoriteIds([]);
    setFavorites([]);
  }, []);

  if (favoriteIds.length === 0) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-8">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-foreground mb-2">お気に入り</h1>
          <p className="text-sm text-muted-foreground">
            お気に入り登録した議員のスコアを一覧で確認できます
          </p>
        </div>
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16">
            <svg className="h-16 w-16 text-muted-foreground/50 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
            </svg>
            <p className="text-muted-foreground font-medium mb-2">
              お気に入りの議員がまだ登録されていません
            </p>
            <p className="text-sm text-muted-foreground mb-6">
              議員詳細ページの★ボタンからお気に入りに追加できます
            </p>
            <Button asChild>
              <Link href="/members">議員一覧へ</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground mb-2">お気に入り</h1>
          <p className="text-sm text-muted-foreground">
            {favoriteIds.length}名の議員をウォッチ中
          </p>
        </div>
        <div className="flex items-center gap-2">
          {compareSelection.length >= 2 && (
            <Button size="sm" onClick={() => router.push(`/compare?ids=${compareSelection.join(",")}`)}>
              比較する ({compareSelection.length})
            </Button>
          )}
          <Button variant="outline" size="sm" onClick={handleClearAll}>
            全てクリア
          </Button>
        </div>
      </div>

      {isLoading ? (
        <LoadingSpinner />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {members.map((member) => {
            const latestScore = member.scores.length > 0 ? member.scores[0] : null;
            const gradeColor = latestScore
              ? GRADE_COLORS[latestScore.grade] || "bg-gray-300"
              : "bg-gray-300";
            return (
              <Card key={member.id} className={`relative ${compareSelection.includes(member.id) ? "ring-2 ring-blue-500" : ""}`}>
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-2">
                      <button
                        type="button"
                        onClick={() => {
                          setCompareSelection((prev) =>
                            prev.includes(member.id)
                              ? prev.filter((id) => id !== member.id)
                              : prev.length < 4 ? [...prev, member.id] : prev,
                          );
                        }}
                        className={`mt-1 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded border transition-colors ${
                          compareSelection.includes(member.id)
                            ? "bg-blue-600 border-blue-600 text-white"
                            : compareSelection.length >= 4
                              ? "border-muted bg-muted/50 cursor-not-allowed"
                              : "border-slate-300 hover:border-blue-400"
                        }`}
                        aria-label={`${member.name}を比較に追加`}
                      >
                        {compareSelection.includes(member.id) && (
                          <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                          </svg>
                        )}
                      </button>
                    <div>
                      <Link href={`/members/${member.id}`} className="text-base font-bold text-blue-600 hover:underline">
                        {member.name}
                      </Link>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge variant="outline" className="text-xs">
                          {CHAMBER_LABELS[member.chamber]}
                        </Badge>
                        <span className="text-xs text-muted-foreground">{member.party ?? "無所属"}</span>
                      </div>
                    </div>
                    </div>
                    <div className="flex items-center gap-1">
                      <FavoriteButton memberId={member.id} />
                      <button
                        type="button"
                        onClick={() => handleRemove(member.id)}
                        className="text-muted-foreground/50 hover:text-red-400 transition-colors"
                        aria-label="お気に入りから削除"
                      >
                        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  {latestScore ? (
                    <div className="flex items-center gap-4">
                      <span className={`inline-flex h-10 w-10 items-center justify-center rounded-full text-white text-sm font-bold ${gradeColor}`}>
                        {latestScore.grade}
                      </span>
                      <div>
                        <p className="text-lg font-bold">{latestScore.total.toFixed(1)}</p>
                        <p className="text-xs text-muted-foreground">総合スコア</p>
                      </div>
                      <div className="ml-auto grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-muted-foreground">
                        <span>立法 {latestScore.legislative_activity.toFixed(0)}</span>
                        <span>投票 {latestScore.voting_behavior.toFixed(0)}</span>
                        <span>影響 {latestScore.policy_influence.toFixed(0)}</span>
                        <span>透明 {latestScore.transparency.toFixed(0)}</span>
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground/70">スコアデータなし</p>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
