"use client";

import { useCallback, useState } from "react";
import Link from "next/link";
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

function useFavoriteMember(id: number | null) {
  return useSWR<MemberDetail>(
    id !== null ? `/members/${id}` : null,
    swrFetcher,
  );
}

export default function FavoritesContent() {
  const [favoriteIds, setFavoriteIds] = useState<number[]>(() => getFavorites());

  // 最大20名分を取得
  const ids = favoriteIds.slice(0, 20);
  const results = [
    useFavoriteMember(ids[0] ?? null),
    useFavoriteMember(ids[1] ?? null),
    useFavoriteMember(ids[2] ?? null),
    useFavoriteMember(ids[3] ?? null),
    useFavoriteMember(ids[4] ?? null),
    useFavoriteMember(ids[5] ?? null),
    useFavoriteMember(ids[6] ?? null),
    useFavoriteMember(ids[7] ?? null),
    useFavoriteMember(ids[8] ?? null),
    useFavoriteMember(ids[9] ?? null),
    useFavoriteMember(ids[10] ?? null),
    useFavoriteMember(ids[11] ?? null),
    useFavoriteMember(ids[12] ?? null),
    useFavoriteMember(ids[13] ?? null),
    useFavoriteMember(ids[14] ?? null),
    useFavoriteMember(ids[15] ?? null),
    useFavoriteMember(ids[16] ?? null),
    useFavoriteMember(ids[17] ?? null),
    useFavoriteMember(ids[18] ?? null),
    useFavoriteMember(ids[19] ?? null),
  ].slice(0, ids.length);

  const isLoading = results.some((r) => r.isLoading);
  const members = results
    .map((r) => r.data)
    .filter((d): d is MemberDetail => d !== undefined);

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
          <h1 className="text-2xl font-bold text-slate-800 mb-2">お気に入り</h1>
          <p className="text-sm text-slate-500">
            お気に入り登録した議員のスコアを一覧で確認できます
          </p>
        </div>
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16">
            <svg className="h-16 w-16 text-slate-300 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
            </svg>
            <p className="text-slate-600 font-medium mb-2">
              お気に入りの議員がまだ登録されていません
            </p>
            <p className="text-sm text-slate-500 mb-6">
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
          <h1 className="text-2xl font-bold text-slate-800 mb-2">お気に入り</h1>
          <p className="text-sm text-slate-500">
            {favoriteIds.length}名の議員をウォッチ中
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={handleClearAll}>
          全てクリア
        </Button>
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
              <Card key={member.id} className="relative">
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between">
                    <div>
                      <Link href={`/members/${member.id}`} className="text-base font-bold text-blue-600 hover:underline">
                        {member.name}
                      </Link>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge variant="outline" className="text-xs">
                          {CHAMBER_LABELS[member.chamber]}
                        </Badge>
                        <span className="text-xs text-slate-500">{member.party ?? "無所属"}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      <FavoriteButton memberId={member.id} />
                      <button
                        type="button"
                        onClick={() => handleRemove(member.id)}
                        className="text-slate-300 hover:text-red-400 transition-colors"
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
                        <p className="text-xs text-slate-500">総合スコア</p>
                      </div>
                      <div className="ml-auto grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-slate-500">
                        <span>立法 {latestScore.legislative_activity.toFixed(0)}</span>
                        <span>投票 {latestScore.voting_behavior.toFixed(0)}</span>
                        <span>影響 {latestScore.policy_influence.toFixed(0)}</span>
                        <span>透明 {latestScore.transparency.toFixed(0)}</span>
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm text-slate-400">スコアデータなし</p>
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
