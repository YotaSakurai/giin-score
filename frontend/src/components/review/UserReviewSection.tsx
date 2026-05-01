"use client";

import { useState, useMemo, useCallback, useEffect } from "react";
import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Slider } from "@/components/ui/slider";
import { Pagination } from "@/components/ui/pagination";
import { LoadingSpinner } from "@/components/ui/loading";
import { useReviews, useReviewSummary } from "@/lib/hooks";
import { postApi, deleteApi } from "@/lib/api";
import { getReviewerId, getDisplayName, setDisplayName } from "@/lib/reviewer";
import type { ScoreDetail, ReviewResponse } from "@/lib/types";
import { AXIS_LABELS } from "@/lib/types";

interface UserReviewSectionProps {
  memberId: number;
  aiScores: ScoreDetail | null;
}

const AXES = [
  "legislative_activity",
  "voting_behavior",
  "policy_influence",
  "transparency",
  "question_quality",
] as const;

type AxisKey = (typeof AXES)[number];

export function UserReviewSection({ memberId, aiScores }: UserReviewSectionProps) {
  const [reviewerId] = useState(() => getReviewerId());
  const [sort, setSort] = useState<"likes" | "newest">("likes");
  const [page, setPage] = useState(1);

  const { data: reviewData, isLoading: reviewsLoading, mutate: mutateReviews } = useReviews(memberId, {
    sort,
    page,
    per_page: 10,
    liker_id: reviewerId || undefined,
  });
  const { data: summary, mutate: mutateSummary } = useReviewSummary(memberId);

  const reviews = useMemo(() => reviewData?.items ?? [], [reviewData?.items]);
  const reviewPages = reviewData?.pages ?? 0;

  const myReview = useMemo(
    () => reviews.find((r) => r.reviewer_id === reviewerId),
    [reviews, reviewerId],
  );

  // --- Radar chart data ---
  const radarData = useMemo(() => {
    return AXES.map((key) => ({
      axis: AXIS_LABELS[key],
      AI: aiScores ? aiScores[key] : 0,
      user: summary && summary.review_count > 0
        ? summary[`average_${key}` as keyof typeof summary] as number
        : null,
    }));
  }, [aiScores, summary]);

  const refreshAll = useCallback(() => {
    mutateReviews();
    mutateSummary();
  }, [mutateReviews, mutateSummary]);

  return (
    <div className="space-y-6">
      {/* A) レーダーチャート重畳 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">AI評価 vs 市民評価</CardTitle>
          <p className="text-xs text-muted-foreground">
            青: AIスコア / オレンジ: ユーザー平均
            {summary && summary.review_count > 0 && ` (${summary.review_count}件)`}
          </p>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-center">
            <div className="md:col-span-2 h-72">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={radarData}>
                  <PolarGrid />
                  <PolarAngleAxis dataKey="axis" tick={{ fontSize: 12 }} />
                  <PolarRadiusAxis domain={[0, 100]} tick={{ fontSize: 10 }} />
                  <Radar
                    name="AI評価"
                    dataKey="AI"
                    stroke="#3b82f6"
                    fill="#3b82f6"
                    fillOpacity={0.2}
                  />
                  {summary && summary.review_count > 0 && (
                    <Radar
                      name="市民評価"
                      dataKey="user"
                      stroke="#f59e0b"
                      fill="#f59e0b"
                      fillOpacity={0.2}
                    />
                  )}
                  <Legend />
                </RadarChart>
              </ResponsiveContainer>
            </div>
            {/* B) スコアカード比較 */}
            <div className="space-y-3">
              <div className="rounded-lg border p-4 text-center">
                <p className="text-xs text-muted-foreground mb-1">AI総合</p>
                <p className="text-2xl font-bold text-blue-600">
                  {aiScores ? aiScores.total.toFixed(1) : "-"}
                </p>
              </div>
              <div className="rounded-lg border p-4 text-center">
                <p className="text-xs text-muted-foreground mb-1">市民評価平均</p>
                <p className="text-2xl font-bold text-amber-600">
                  {summary && summary.review_count > 0 ? summary.average_total.toFixed(1) : "-"}
                </p>
                <p className="text-xs text-muted-foreground">
                  {summary ? `${summary.review_count}件` : "0件"}
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* C) レビューフォーム */}
      <ReviewForm
        memberId={memberId}
        reviewerId={reviewerId}
        existingReview={myReview}
        onSubmit={refreshAll}
      />

      {/* D) レビュー一覧 */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">レビュー一覧</CardTitle>
            <div className="flex gap-2">
              <button
                onClick={() => { setSort("likes"); setPage(1); }}
                className={`text-xs px-3 py-1 rounded-full border ${sort === "likes" ? "bg-primary text-primary-foreground" : "bg-background"}`}
              >
                いいね順
              </button>
              <button
                onClick={() => { setSort("newest"); setPage(1); }}
                className={`text-xs px-3 py-1 rounded-full border ${sort === "newest" ? "bg-primary text-primary-foreground" : "bg-background"}`}
              >
                新着順
              </button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {reviewsLoading ? (
            <LoadingSpinner />
          ) : reviews.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-4">
              まだレビューがありません。最初のレビューを投稿しましょう！
            </p>
          ) : (
            <>
              <div className="space-y-3">
                {reviews.map((review) => (
                  <ReviewCard
                    key={review.id}
                    review={review}
                    isOwn={review.reviewer_id === reviewerId}
                    reviewerId={reviewerId}
                    onUpdate={refreshAll}
                  />
                ))}
              </div>
              <Pagination page={page} pages={reviewPages} onPageChange={setPage} />
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// --- ReviewForm ---

function ReviewForm({
  memberId,
  reviewerId,
  existingReview,
  onSubmit,
}: {
  memberId: number;
  reviewerId: string;
  existingReview?: ReviewResponse;
  onSubmit: () => void;
}) {
  const [scores, setScores] = useState<Record<AxisKey, number>>({
    legislative_activity: 50,
    voting_behavior: 50,
    policy_influence: 50,
    transparency: 50,
    question_quality: 50,
  });
  const [comment, setComment] = useState("");
  const [displayName, setDisplayNameState] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [expanded, setExpanded] = useState(false);

  // Prefill from existing review
  useEffect(() => {
    if (existingReview) {
      setScores({
        legislative_activity: existingReview.legislative_activity,
        voting_behavior: existingReview.voting_behavior,
        policy_influence: existingReview.policy_influence,
        transparency: existingReview.transparency,
        question_quality: existingReview.question_quality,
      });
      setComment(existingReview.comment ?? "");
      setDisplayNameState(existingReview.display_name ?? "");
    }
  }, [existingReview]);

  // Load saved display name
  useEffect(() => {
    if (!existingReview) {
      const saved = getDisplayName();
      if (saved) setDisplayNameState(saved);
    }
  }, [existingReview]);

  const total = useMemo(
    () => Object.values(scores).reduce((s, v) => s + v, 0) / 5,
    [scores],
  );

  const handleSubmit = async () => {
    if (!reviewerId) return;
    setSubmitting(true);
    try {
      if (displayName) setDisplayName(displayName);
      await postApi(`/members/${memberId}/reviews`, {
        reviewer_id: reviewerId,
        display_name: displayName || null,
        ...scores,
        comment: comment || null,
      });
      onSubmit();
      if (!existingReview) {
        setExpanded(false);
      }
    } catch {
      // TODO: error handling
    } finally {
      setSubmitting(false);
    }
  };

  if (!expanded && !existingReview) {
    return (
      <Card>
        <CardContent className="p-4 text-center">
          <button
            onClick={() => setExpanded(true)}
            className="text-sm text-blue-600 hover:underline font-medium"
          >
            この議員を評価する
          </button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">
          {existingReview ? "あなたの評価を更新" : "この議員を評価する"}
        </CardTitle>
        <p className="text-xs text-muted-foreground">各軸を0-100で評価してください</p>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <label className="text-sm text-muted-foreground">表示名（任意）</label>
          <input
            type="text"
            value={displayName}
            onChange={(e) => setDisplayNameState(e.target.value)}
            placeholder="匿名"
            maxLength={50}
            className="mt-1 w-full rounded-md border px-3 py-2 text-sm bg-background"
          />
        </div>

        {AXES.map((key) => (
          <div key={key} className="flex items-center gap-4">
            <span className="text-sm text-foreground/80 w-24">{AXIS_LABELS[key]}</span>
            <Slider
              value={[scores[key]]}
              onValueChange={([v]) => setScores((prev) => ({ ...prev, [key]: v }))}
              max={100}
              min={0}
              step={5}
              className="flex-1"
            />
            <span className="text-sm font-mono text-muted-foreground w-10 text-right">
              {scores[key]}
            </span>
          </div>
        ))}

        <div className="text-center text-sm text-muted-foreground">
          総合: <span className="font-bold text-foreground">{total.toFixed(1)}</span>
        </div>

        <div>
          <label className="text-sm text-muted-foreground">コメント（任意・最大1000文字）</label>
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            maxLength={1000}
            rows={3}
            placeholder="この議員に対するコメントを入力..."
            className="mt-1 w-full rounded-md border px-3 py-2 text-sm bg-background resize-none"
          />
          <p className="text-xs text-muted-foreground text-right">{comment.length}/1000</p>
        </div>

        <div className="flex gap-2">
          <button
            onClick={handleSubmit}
            disabled={submitting || !reviewerId}
            className="px-4 py-2 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 disabled:opacity-50"
          >
            {submitting ? "送信中..." : existingReview ? "更新する" : "投稿する"}
          </button>
          {!existingReview && (
            <button
              onClick={() => setExpanded(false)}
              className="px-4 py-2 rounded-md border text-sm"
            >
              キャンセル
            </button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// --- ReviewCard ---

function ReviewCard({
  review,
  isOwn,
  reviewerId,
  onUpdate,
}: {
  review: ReviewResponse;
  isOwn: boolean;
  reviewerId: string;
  onUpdate: () => void;
}) {
  const [liking, setLiking] = useState(false);

  const handleLike = async () => {
    if (!reviewerId || liking) return;
    setLiking(true);
    try {
      await postApi(`/reviews/${review.id}/like`, { liker_id: reviewerId });
      onUpdate();
    } catch {
      // ignore
    } finally {
      setLiking(false);
    }
  };

  const handleDelete = async () => {
    try {
      await deleteApi(`/reviews/${review.id}?reviewer_id=${encodeURIComponent(reviewerId)}`);
      onUpdate();
    } catch {
      // ignore
    }
  };

  const totalGrade =
    review.total >= 80 ? "A" : review.total >= 60 ? "B" : review.total >= 40 ? "C" : review.total >= 20 ? "D" : "F";

  const gradeColor: Record<string, string> = {
    A: "bg-emerald-500",
    B: "bg-blue-500",
    C: "bg-yellow-500",
    D: "bg-orange-500",
    F: "bg-red-500",
  };

  return (
    <div className={`rounded-lg border p-4 ${isOwn ? "border-blue-300 bg-blue-50/30 dark:border-blue-800 dark:bg-blue-950/20" : ""}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className={`inline-flex h-7 w-7 items-center justify-center rounded-full text-white text-xs font-bold ${gradeColor[totalGrade]}`}>
            {totalGrade}
          </span>
          <div>
            <p className="text-sm font-medium">
              {review.display_name || "匿名"}
              {isOwn && <Badge variant="outline" className="ml-2 text-xs">あなた</Badge>}
            </p>
            <p className="text-xs text-muted-foreground">
              {new Date(review.created_at).toLocaleDateString("ja-JP")} / 総合 {review.total.toFixed(1)}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleLike}
            disabled={liking}
            className={`flex items-center gap-1 text-xs px-2 py-1 rounded-full border transition-colors ${review.is_liked ? "bg-red-50 border-red-200 text-red-600 dark:bg-red-950/30 dark:border-red-800" : "hover:bg-muted"}`}
          >
            <svg className="h-3.5 w-3.5" fill={review.is_liked ? "currentColor" : "none"} viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
            </svg>
            {review.like_count}
          </button>
        </div>
      </div>

      {/* 5軸ミニバー */}
      <div className="mt-3 grid grid-cols-5 gap-1">
        {AXES.map((key) => (
          <div key={key} className="text-center">
            <p className="text-[10px] text-muted-foreground truncate">{AXIS_LABELS[key]}</p>
            <div className="h-1.5 w-full rounded-full bg-muted mt-0.5">
              <div
                className="h-1.5 rounded-full bg-amber-500"
                style={{ width: `${Math.min(review[key], 100)}%` }}
              />
            </div>
            <p className="text-[10px] font-medium">{review[key].toFixed(0)}</p>
          </div>
        ))}
      </div>

      {review.comment && (
        <p className="mt-3 text-sm text-muted-foreground whitespace-pre-wrap">{review.comment}</p>
      )}

      {isOwn && (
        <div className="mt-3 flex gap-2">
          <button
            onClick={handleDelete}
            className="text-xs text-red-500 hover:underline"
          >
            削除
          </button>
        </div>
      )}
    </div>
  );
}
