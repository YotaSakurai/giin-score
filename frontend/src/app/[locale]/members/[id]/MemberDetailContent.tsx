"use client";

import { useState, useMemo, use, useCallback } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Link } from "@/i18n/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Slider } from "@/components/ui/slider";
import { Pagination } from "@/components/ui/pagination";
import { LoadingSpinner } from "@/components/ui/loading";
import { ErrorMessage } from "@/components/ui/error";
import { ScoreRadarChart } from "@/components/score/ScoreRadarChart";
import { ScoreHistoryChart } from "@/components/score/ScoreHistoryChart";
import { ScoreCard } from "@/components/score/ScoreCard";
import { ScoreBreakdown } from "@/components/score/ScoreBreakdown";
import { ShareButton } from "@/components/ShareButton";
import { FavoriteButton } from "@/components/FavoriteButton";
import { CHAMBER_LABELS, AXIS_LABELS, GRADE_COLORS } from "@/lib/types";
import { VOTE_LABELS, VOTE_COLORS, SCORE_DESCRIPTIONS, GRADE_DESCRIPTIONS } from "@/lib/constants";
import { useMember, useMemberSpeeches, useMemberVotes, useVotePattern, useSpeechQuality, useWrittenQuestions, useStats, useMembers, useReviewSummary } from "@/lib/hooks";
import { UserReviewSection } from "@/components/review/UserReviewSection";

interface MemberDetailContentProps {
  params: Promise<{ id: string }>;
}

/** 各軸のスコアを全体平均と比較して差分情報を返す */
function useScoreComparison(
  scores: { legislative_activity: number; voting_behavior: number; policy_influence: number; transparency: number; question_quality: number; total: number } | null,
  chamber?: string,
) {
  const { data: stats } = useStats(chamber ? { chamber } : undefined);
  return useMemo(() => {
    if (!scores || !stats) return null;
    const avg = stats.average_score;
    const axes = [
      { key: "legislative_activity" as const, label: "立法活動" },
      { key: "voting_behavior" as const, label: "投票行動" },
      { key: "policy_influence" as const, label: "政策影響力" },
      { key: "transparency" as const, label: "透明性" },
      { key: "question_quality" as const, label: "質問品質" },
    ];
    // Overall average is total score average; for per-axis we use 50 as the expected center since they're percentile ranks
    const comparisons = axes.map((a) => ({
      ...a,
      value: scores[a.key],
      avgDiff: scores[a.key] - 50,
    }));
    return {
      totalDiff: scores.total - avg,
      axes: comparisons,
    };
  }, [scores, stats]);
}

/** スコアパターンから議員の特徴を自動生成するテキスト */
function generateMemberSummary(
  scores: { legislative_activity: number; voting_behavior: number; policy_influence: number; transparency: number; question_quality: number; total: number; grade: string },
): string[] {
  const lines: string[] = [];

  // 総合評価
  if (scores.grade === "A") {
    lines.push("全体的に非常に活発な議会活動を行っています。");
  } else if (scores.grade === "B") {
    lines.push("平均以上の議会活動を行っています。");
  } else if (scores.grade === "F") {
    lines.push("議会活動が全体の中で非常に低い水準にあります。");
  }

  // 強み（70以上）
  const axes = [
    { key: "legislative_activity", label: "立法活動", value: scores.legislative_activity },
    { key: "voting_behavior", label: "投票行動", value: scores.voting_behavior },
    { key: "policy_influence", label: "政策影響力", value: scores.policy_influence },
    { key: "transparency", label: "透明性", value: scores.transparency },
    { key: "question_quality", label: "質問品質", value: scores.question_quality },
  ];
  const strengths = axes.filter((a) => a.value >= 70).map((a) => a.label);
  const weaknesses = axes.filter((a) => a.value < 30).map((a) => a.label);

  if (strengths.length > 0) {
    lines.push(`強み: ${strengths.join("・")}が高水準です。`);
  }
  if (weaknesses.length > 0) {
    lines.push(`課題: ${weaknesses.join("・")}が低水準です。`);
  }

  // 特徴的なパターン
  if (scores.legislative_activity >= 70 && scores.policy_influence < 30) {
    lines.push("法案提出は活発ですが、成立に至る成果が少ない傾向があります。");
  }
  if (scores.policy_influence >= 70 && scores.legislative_activity < 40) {
    lines.push("法案の成立率が高く、少数精鋭の提案で成果を出すタイプです。");
  }
  if (scores.question_quality >= 70 && scores.voting_behavior >= 70) {
    lines.push("質問の質が高く、投票にも積極的に参加しており、堅実な議員活動を行っています。");
  }
  if (scores.voting_behavior < 30) {
    lines.push("投票への参加率が低く、採決に出席していない可能性があります。");
  }
  if (scores.question_quality < 20 && scores.legislative_activity < 20) {
    lines.push("質疑・立法とも活動量が非常に少ない状態です。");
  }

  return lines;
}

export default function MemberDetailContent({ params }: MemberDetailContentProps) {
  const { id } = use(params);
  const memberId = Number(id);
  const router = useRouter();
  const searchParams = useSearchParams();
  const activeTab = searchParams.get("tab") || "speeches";

  const setActiveTab = useCallback((tab: string) => {
    const params = new URLSearchParams(searchParams.toString());
    if (tab === "speeches") {
      params.delete("tab");
    } else {
      params.set("tab", tab);
    }
    const qs = params.toString();
    router.replace(qs ? `?${qs}` : ``, { scroll: false });
  }, [router, searchParams]);

  const { data: member, error, isLoading, mutate } = useMember(memberId);

  // Speeches state
  const [speechPage, setSpeechPage] = useState(1);
  const {
    data: speechData,
    isLoading: speechLoading,
  } = useMemberSpeeches(memberId, speechPage, 10);
  const speeches = speechData?.items ?? [];
  const speechPages = speechData?.pages ?? 0;

  // Votes state
  const [votePage, setVotePage] = useState(1);
  const {
    data: voteData,
    isLoading: voteLoading,
  } = useMemberVotes(memberId, votePage, 10);
  const votes = voteData?.items ?? [];
  const votePages = voteData?.pages ?? 0;

  // Vote pattern
  const { data: votePattern } = useVotePattern(memberId);

  // Speech quality state
  const [qualityPage, setQualityPage] = useState(1);
  const {
    data: qualityData,
    isLoading: qualityLoading,
  } = useSpeechQuality(memberId, qualityPage, 10);
  const qualityItems = qualityData?.items ?? [];
  const qualityPages = qualityData?.pages ?? 0;

  // Written questions state
  const [wqPage, setWqPage] = useState(1);
  const {
    data: wqData,
    isLoading: wqLoading,
  } = useWrittenQuestions(memberId, wqPage, 10);
  const wqItems = wqData?.items ?? [];
  const wqPages = wqData?.pages ?? 0;

  const [weights, setWeights] = useState({
    legislative_activity: 25,
    voting_behavior: 20,
    policy_influence: 20,
    transparency: 15,
    question_quality: 20,
  });

  const latestScore = member?.scores?.[0] ?? null;
  const prevScore = member?.scores?.[1] ?? null;

  // 前会期との差分
  const scoreDiff = useMemo(() => {
    if (!latestScore || !prevScore) return null;
    return {
      total: latestScore.total - prevScore.total,
      legislative_activity: latestScore.legislative_activity - prevScore.legislative_activity,
      voting_behavior: latestScore.voting_behavior - prevScore.voting_behavior,
      policy_influence: latestScore.policy_influence - prevScore.policy_influence,
      transparency: latestScore.transparency - prevScore.transparency,
      question_quality: latestScore.question_quality - prevScore.question_quality,
    };
  }, [latestScore, prevScore]);

  const customTotal = useMemo(() => {
    if (!latestScore) return 0;
    const sum = weights.legislative_activity + weights.voting_behavior + weights.policy_influence + weights.transparency + weights.question_quality;
    if (sum === 0) return 0;
    return (
      (latestScore.legislative_activity * weights.legislative_activity +
        latestScore.voting_behavior * weights.voting_behavior +
        latestScore.policy_influence * weights.policy_influence +
        latestScore.transparency * weights.transparency +
        latestScore.question_quality * weights.question_quality) / sum
    );
  }, [latestScore, weights]);

  const customGrade = customTotal >= 80 ? "A" : customTotal >= 60 ? "B" : customTotal >= 40 ? "C" : customTotal >= 20 ? "D" : "F";

  // 平均比較
  const comparison = useScoreComparison(
    latestScore ? {
      legislative_activity: latestScore.legislative_activity,
      voting_behavior: latestScore.voting_behavior,
      policy_influence: latestScore.policy_influence,
      transparency: latestScore.transparency,
      question_quality: latestScore.question_quality,
      total: latestScore.total,
    } : null,
    member?.chamber,
  );

  // 同じ選挙区の議員
  const { data: sameDistrictData } = useMembers(
    member?.district
      ? { district: member.district, sort_by: "total", sort_order: "desc", per_page: 10 }
      : undefined,
  );
  const sameDistrictMembers = useMemo(() => {
    if (!sameDistrictData?.items) return [];
    return sameDistrictData.items.filter((m) => m.id !== memberId);
  }, [sameDistrictData, memberId]);

  // レビューサマリー
  const { data: reviewSummary } = useReviewSummary(memberId);

  // 特徴サマリー
  const summaryLines = useMemo(() => {
    if (!latestScore) return [];
    return generateMemberSummary({
      legislative_activity: latestScore.legislative_activity,
      voting_behavior: latestScore.voting_behavior,
      policy_influence: latestScore.policy_influence,
      transparency: latestScore.transparency,
      question_quality: latestScore.question_quality,
      total: latestScore.total,
      grade: latestScore.grade,
    });
  }, [latestScore]);

  if (isLoading) return <div className="mx-auto max-w-7xl px-4 py-8"><LoadingSpinner /></div>;
  if (error) return <div className="mx-auto max-w-7xl px-4 py-8"><ErrorMessage message={error instanceof Error ? error.message : "データの取得に失敗しました"} onRetry={() => mutate()} /></div>;
  if (!member) return <div className="mx-auto max-w-7xl px-4 py-8">議員が見つかりません</div>;

  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://giinscore.jp";
  const shareUrl = `${siteUrl}/members/${memberId}`;
  const shareTitle = latestScore
    ? `${member.name}（${member.party ?? "無所属"}）国会活動スコア\n総合${latestScore.total.toFixed(1)}点 グレード${latestScore.grade}\n立法${latestScore.legislative_activity.toFixed(0)} 投票${latestScore.voting_behavior.toFixed(0)} 影響${latestScore.policy_influence.toFixed(0)} 透明${latestScore.transparency.toFixed(0)} 質問${latestScore.question_quality.toFixed(0)}${summaryLines.length > 0 ? `\n${summaryLines[0]}` : ""} | GiinScore`
    : `${member.name}のスコア | GiinScore`;

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      {/* パンくず */}
      <nav aria-label="パンくずリスト" className="text-sm text-muted-foreground mb-6">
        <Link href="/members" className="hover:text-primary">議員一覧</Link>
        <span className="mx-2">/</span>
        <span className="text-foreground">{member.name}</span>
      </nav>

      {/* 議員情報ヘッダー */}
      <div className="flex flex-col md:flex-row gap-6 mb-8">
        <div className="flex items-start gap-4 flex-1">
          <div className="h-20 w-20 rounded-full bg-muted flex items-center justify-center text-2xl font-bold text-muted-foreground">
            {member.name.charAt(0)}
          </div>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-foreground">{member.name}</h1>
              <FavoriteButton memberId={member.id} />
              <ShareButton title={shareTitle} url={shareUrl} />
            </div>
            {member.name_reading && <p className="text-sm text-muted-foreground">{member.name_reading}</p>}
            <div className="flex gap-2 mt-2 flex-wrap">
              <Badge variant="outline">{CHAMBER_LABELS[member.chamber]}</Badge>
              <Badge variant="secondary">{member.party ?? "無所属"}</Badge>
              {member.district && (
                <Link href={`/members?district=${encodeURIComponent(member.district)}`}>
                  <Badge variant="secondary" className="cursor-pointer hover:bg-secondary/80">{member.district}</Badge>
                </Link>
              )}
            </div>
          </div>
        </div>
      </div>

      {latestScore ? (
        <>
          {/* 議員特徴サマリー */}
          {summaryLines.length > 0 && (
            <Card className="mb-8 border-blue-200 dark:border-blue-800 bg-blue-50/30 dark:bg-blue-950/20">
              <CardContent className="p-4">
                <h2 className="text-sm font-semibold text-foreground mb-2">この議員の特徴</h2>
                <ul className="space-y-1">
                  {summaryLines.map((line, i) => (
                    <li key={i} className="text-sm text-muted-foreground flex items-start gap-2">
                      <span className="mt-1 h-1.5 w-1.5 rounded-full bg-blue-500 shrink-0" />
                      {line}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          {/* スコア概要 */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div>
              <ScoreCard total={customTotal} grade={customGrade} label="総合スコア" />
              <div className="mt-2 text-center space-y-1">
                {comparison && (
                  <span className={`text-sm font-medium ${comparison.totalDiff >= 0 ? "text-emerald-600" : "text-red-500"}`}>
                    全体平均{comparison.totalDiff >= 0 ? "+" : ""}{comparison.totalDiff.toFixed(1)}
                  </span>
                )}
                {scoreDiff && (
                  <p className={`text-xs ${scoreDiff.total >= 0 ? "text-emerald-600" : "text-red-500"}`}>
                    前会期比 {scoreDiff.total >= 0 ? "+" : ""}{scoreDiff.total.toFixed(1)}pt
                    {prevScore?.grade && latestScore?.grade && prevScore.grade !== latestScore.grade && (
                      <span className="ml-1">({prevScore.grade}→{latestScore.grade})</span>
                    )}
                  </p>
                )}
              </div>
            </div>
            <div className="md:col-span-2">
              <Card>
                <CardContent className="p-4">
                  <ScoreRadarChart
                    legislative_activity={latestScore.legislative_activity}
                    voting_behavior={latestScore.voting_behavior}
                    policy_influence={latestScore.policy_influence}
                    transparency={latestScore.transparency}
                    question_quality={latestScore.question_quality}
                  />
                  {reviewSummary && reviewSummary.review_count > 0 && (
                    <div className="mt-2 text-center text-sm text-muted-foreground">
                      レビュー {reviewSummary.review_count}件 | ユーザー平均 {reviewSummary.average_total.toFixed(1)}点
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </div>

          {/* 5軸の平均比較 */}
          {comparison && (
            <Card className="mb-8">
              <CardHeader>
                <CardTitle className="text-base">全体平均との比較</CardTitle>
                <p className="text-xs text-muted-foreground">50が同条件の議員の中央値です。50を超えていれば平均以上、下回っていれば平均以下です。</p>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {comparison.axes.map((axis) => {
                    const pct = Math.min(axis.value, 100);
                    const isAbove = axis.value >= 50;
                    return (
                      <div key={axis.key} className="flex items-center gap-3">
                        <span className="text-sm w-20 shrink-0">{axis.label}</span>
                        <div className="flex-1 relative h-6">
                          {/* 背景バー */}
                          <div className="absolute inset-0 rounded-full bg-muted" />
                          {/* 中央線 */}
                          <div className="absolute top-0 bottom-0 left-1/2 w-px bg-border z-10" />
                          {/* スコアバー */}
                          <div
                            className={`absolute top-0 bottom-0 rounded-full ${isAbove ? "bg-emerald-500/30" : "bg-red-500/30"}`}
                            style={{
                              left: isAbove ? "50%" : `${pct}%`,
                              width: `${Math.abs(pct - 50)}%`,
                            }}
                          />
                          {/* ドット */}
                          <div
                            className={`absolute top-1/2 -translate-y-1/2 h-4 w-4 rounded-full border-2 border-white shadow ${isAbove ? "bg-emerald-500" : "bg-red-500"}`}
                            style={{ left: `calc(${pct}% - 8px)` }}
                          />
                        </div>
                        <span className={`text-sm font-medium w-12 text-right ${isAbove ? "text-emerald-600" : "text-red-500"}`}>
                          {axis.value.toFixed(0)}
                        </span>
                        <span className="group relative cursor-help">
                          <svg className="h-3.5 w-3.5 text-muted-foreground/50 hover:text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <circle cx="12" cy="12" r="10" />
                            <path d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3" />
                            <line x1="12" y1="17" x2="12.01" y2="17" />
                          </svg>
                          <span className="invisible group-hover:visible absolute bottom-full right-0 mb-2 w-56 rounded-lg bg-popover border border-border p-2 text-xs text-popover-foreground shadow-lg z-50">
                            {SCORE_DESCRIPTIONS[axis.key]?.short}
                          </span>
                        </span>
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          )}

          {/* グレード解説 */}
          <div className="mb-8 flex items-center gap-3 text-sm">
            <span className={`inline-flex h-8 w-8 items-center justify-center rounded-full text-white text-sm font-bold ${GRADE_COLORS[latestScore.grade] || "bg-gray-300"}`}>
              {latestScore.grade}
            </span>
            <span className="text-muted-foreground">{GRADE_DESCRIPTIONS[latestScore.grade]}</span>
          </div>

          {/* 重みカスタマイズスライダー */}
          <Card className="mb-8">
            <CardHeader>
              <CardTitle className="text-base">スコアの重みカスタマイズ</CardTitle>
              <p className="text-xs text-muted-foreground">各軸の重みを調整して、あなた独自の評価基準でスコアを算出できます</p>
            </CardHeader>
            <CardContent className="space-y-4">
              {(Object.keys(weights) as Array<keyof typeof weights>).map((key) => (
                <div key={key} className="flex items-center gap-4">
                  <span className="text-sm text-foreground/80 w-24">{AXIS_LABELS[key]}</span>
                  <Slider
                    value={[weights[key]]}
                    onValueChange={([v]) => setWeights((prev) => ({ ...prev, [key]: v }))}
                    max={100}
                    min={0}
                    step={5}
                    className="flex-1"
                  />
                  <span className="text-sm font-mono text-muted-foreground w-12 text-right">{weights[key]}%</span>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* スコア内訳 */}
          <div className="mb-8">
            <ScoreBreakdown
              breakdown={latestScore.breakdown}
              scores={{
                legislative_activity: latestScore.legislative_activity,
                voting_behavior: latestScore.voting_behavior,
                policy_influence: latestScore.policy_influence,
                transparency: latestScore.transparency,
                question_quality: latestScore.question_quality,
              }}
            />
          </div>

          {/* スコア推移 */}
          {member.scores.length >= 2 && (
            <Card className="mb-8">
              <CardHeader>
                <CardTitle className="text-base">スコア推移</CardTitle>
              </CardHeader>
              <CardContent>
                <ScoreHistoryChart scores={member.scores} />
              </CardContent>
            </Card>
          )}
        </>
      ) : (
        <Card className="mb-8">
          <CardContent className="p-6 text-center text-sm text-muted-foreground">
            スコアデータがまだ計算されていません
          </CardContent>
        </Card>
      )}

      {/* タブ: 発言・投票・法案 */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="speeches">発言履歴</TabsTrigger>
          <TabsTrigger value="speech-quality">質問品質</TabsTrigger>
          <TabsTrigger value="votes">投票記録</TabsTrigger>
          <TabsTrigger value="vote-pattern">投票パターン</TabsTrigger>
          <TabsTrigger value="written-questions">質問主意書</TabsTrigger>
          <TabsTrigger value="user-reviews">市民評価</TabsTrigger>
        </TabsList>

        <TabsContent value="speeches">
          <Card>
            <CardContent className="p-4">
              {speechLoading ? (
                <LoadingSpinner />
              ) : speeches.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-4">発言データがありません</p>
              ) : (
                <>
                  <table className="w-full">
                    <thead>
                      <tr className="border-b text-left text-xs text-muted-foreground">
                        <th scope="col" className="p-2">日付</th>
                        <th scope="col" className="p-2">会議名</th>
                        <th scope="col" className="p-2 text-right">文字数</th>
                        <th scope="col" className="p-2 text-right">リンク</th>
                      </tr>
                    </thead>
                    <tbody>
                      {speeches.map((s, i) => (
                        <tr key={i} className="border-b hover:bg-muted/50">
                          <td className="p-2 text-sm text-muted-foreground">
                            {s.speech_date ?? "-"}
                          </td>
                          <td className="p-2 text-sm">{s.meeting_name ?? "-"}</td>
                          <td className="p-2 text-sm text-right text-muted-foreground">
                            {(s.speech_chars ?? 0).toLocaleString()}字
                          </td>
                          <td className="p-2 text-sm text-right">
                            {s.speech_url ? (
                              <a href={s.speech_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline text-xs">
                                会議録
                              </a>
                            ) : (
                              <span className="text-muted-foreground/50 text-xs">-</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <Pagination page={speechPage} pages={speechPages} onPageChange={setSpeechPage} />
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="speech-quality">
          <Card>
            <CardContent className="p-4">
              {qualityLoading ? (
                <LoadingSpinner />
              ) : qualityItems.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-4">質問品質データがまだ分析されていません</p>
              ) : (
                <>
                  <div className="space-y-3">
                    {qualityItems.map((q) => {
                      const bg = q.overall_quality >= 70
                        ? "border-l-emerald-500"
                        : q.overall_quality >= 40
                          ? "border-l-yellow-500"
                          : "border-l-red-500";
                      return (
                        <div key={q.id} className={`border-l-4 ${bg} rounded-r-lg border p-3`}>
                          <div className="flex items-start justify-between mb-2">
                            <div>
                              <p className="text-sm font-medium">{q.meeting_name ?? "不明"}</p>
                              <p className="text-xs text-muted-foreground">{q.speech_date ?? "-"} / {(q.speech_chars ?? 0).toLocaleString()}字</p>
                            </div>
                            <div className="text-right">
                              <p className="text-lg font-bold">{q.overall_quality.toFixed(0)}</p>
                              <p className="text-xs text-muted-foreground">総合</p>
                            </div>
                          </div>
                          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                            {[
                              { label: "政策関連", value: q.policy_relevance, color: "bg-blue-500" },
                              { label: "建設性", value: q.constructiveness, color: "bg-emerald-500" },
                              { label: "専門性", value: q.expertise, color: "bg-amber-500" },
                              { label: "国益", value: q.national_interest, color: "bg-violet-500" },
                            ].map((axis) => (
                              <div key={axis.label}>
                                <div className="flex items-center justify-between mb-0.5">
                                  <span className="text-muted-foreground">{axis.label}</span>
                                  <span className="font-medium">{axis.value.toFixed(0)}</span>
                                </div>
                                <div className="h-1 w-full rounded-full bg-muted">
                                  <div className={`h-1 rounded-full ${axis.color}`} style={{ width: `${Math.min(axis.value, 100)}%` }} />
                                </div>
                              </div>
                            ))}
                          </div>
                          {q.analysis_summary && (
                            <p className="mt-2 text-xs text-muted-foreground">{q.analysis_summary}</p>
                          )}
                        </div>
                      );
                    })}
                  </div>
                  <Pagination page={qualityPage} pages={qualityPages} onPageChange={setQualityPage} />
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="votes">
          <Card>
            <CardContent className="p-4">
              {voteLoading ? (
                <LoadingSpinner />
              ) : votes.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-4">投票データがありません</p>
              ) : (
                <>
                  <table className="w-full">
                    <thead>
                      <tr className="border-b text-left text-xs text-muted-foreground">
                        <th scope="col" className="p-2">法案名</th>
                        <th scope="col" className="p-2 text-center">投票</th>
                      </tr>
                    </thead>
                    <tbody>
                      {votes.map((v) => (
                        <tr key={v.id} className="border-b hover:bg-muted/50">
                          <td className="p-2 text-sm">{v.bill_title ?? "-"}</td>
                          <td className="p-2 text-center">
                            <Badge className={VOTE_COLORS[v.vote] ?? "bg-muted"}>
                              {VOTE_LABELS[v.vote] ?? v.vote}
                            </Badge>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <Pagination page={votePage} pages={votePages} onPageChange={setVotePage} />
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="vote-pattern">
          <Card>
            <CardContent className="p-4">
              {!votePattern ? (
                <LoadingSpinner />
              ) : votePattern.total_votes === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-4">投票パターンデータがありません</p>
              ) : (
                <div className="space-y-6">
                  {/* サマリーカード with visual gauges */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="rounded-lg border p-4 text-center">
                      <p className="text-xs text-muted-foreground mb-2">投票参加率</p>
                      <div className="relative inline-flex items-center justify-center">
                        <svg className="h-20 w-20" viewBox="0 0 36 36">
                          <path
                            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="3"
                            className="text-muted/40"
                          />
                          <path
                            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="3"
                            strokeDasharray={`${votePattern.participation_rate}, 100`}
                            className={votePattern.participation_rate >= 80 ? "text-emerald-500" : votePattern.participation_rate >= 50 ? "text-yellow-500" : "text-red-500"}
                          />
                        </svg>
                        <span className="absolute text-lg font-bold">{votePattern.participation_rate}%</span>
                      </div>
                      <p className="text-xs text-muted-foreground/70 mt-1">{votePattern.total_votes}/{votePattern.total_votes + votePattern.absent_count}回</p>
                      {votePattern.participation_rate < 50 && (
                        <p className="text-xs text-red-500 mt-1 flex items-center justify-center gap-1">
                          <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                          </svg>
                          参加率が低い
                        </p>
                      )}
                    </div>
                    <div className="rounded-lg border p-4 text-center">
                      <p className="text-xs text-muted-foreground mb-2">造反率</p>
                      <div className="relative inline-flex items-center justify-center">
                        <svg className="h-20 w-20" viewBox="0 0 36 36">
                          <path
                            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="3"
                            className="text-muted/40"
                          />
                          <path
                            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="3"
                            strokeDasharray={`${votePattern.dissent_rate}, 100`}
                            className="text-orange-500"
                          />
                        </svg>
                        <span className="absolute text-lg font-bold">{votePattern.dissent_rate}%</span>
                      </div>
                      <p className="text-xs text-muted-foreground/70 mt-1">{votePattern.dissent_votes}/{votePattern.party_majority_votes}回</p>
                      <p className="text-xs text-muted-foreground/70 mt-0.5">
                        {votePattern.dissent_rate < 5 ? "党方針に忠実" : votePattern.dissent_rate < 20 ? "時々独自判断" : "独自路線が多い"}
                      </p>
                    </div>
                    <div className="rounded-lg border p-4 text-center">
                      <p className="text-xs text-muted-foreground">投票回数</p>
                      <p className="text-2xl font-bold text-foreground/80">{votePattern.total_votes}</p>
                    </div>
                    <div className="rounded-lg border p-4 text-center">
                      <p className="text-xs text-muted-foreground">欠席回数</p>
                      <p className={`text-2xl font-bold ${votePattern.absent_count > 10 ? "text-red-500" : "text-muted-foreground/70"}`}>
                        {votePattern.absent_count}
                      </p>
                      {votePattern.absent_count > 10 && (
                        <p className="text-xs text-red-500 mt-1">欠席が多い</p>
                      )}
                    </div>
                  </div>

                  {/* 造反詳細 */}
                  {votePattern.dissent_details.length > 0 && (
                    <div>
                      <h3 className="text-sm font-semibold text-foreground/80 mb-3">造反投票の詳細</h3>
                      <table className="w-full">
                        <thead>
                          <tr className="border-b text-left text-xs text-muted-foreground">
                            <th scope="col" className="p-2">法案名</th>
                            <th scope="col" className="p-2 text-center">本人の投票</th>
                            <th scope="col" className="p-2 text-center">党の多数派</th>
                          </tr>
                        </thead>
                        <tbody>
                          {votePattern.dissent_details.map((d, i) => (
                            <tr key={i} className="border-b hover:bg-muted/50">
                              <td className="p-2 text-sm">{d.bill_title ?? "-"}</td>
                              <td className="p-2 text-center">
                                <Badge className={VOTE_COLORS[d.member_vote] ?? "bg-muted"}>
                                  {VOTE_LABELS[d.member_vote] ?? d.member_vote}
                                </Badge>
                              </td>
                              <td className="p-2 text-center">
                                <Badge className={VOTE_COLORS[d.party_majority_vote] ?? "bg-muted"}>
                                  {VOTE_LABELS[d.party_majority_vote] ?? d.party_majority_vote}
                                </Badge>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="written-questions">
          <Card>
            <CardContent className="p-4">
              {wqLoading ? (
                <LoadingSpinner />
              ) : wqItems.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-4">質問主意書データがありません</p>
              ) : (
                <>
                  <div className="space-y-3">
                    {wqItems.map((q) => (
                      <div key={q.id} className={`border-l-4 ${q.has_answer ? "border-l-emerald-500" : "border-l-muted"} rounded-r-lg border p-3`}>
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium">{q.title}</p>
                            <p className="text-xs text-muted-foreground mt-1">
                              提出: {q.submitted_date ?? "-"}
                              {q.answer_date && <> / 答弁: {q.answer_date}</>}
                            </p>
                          </div>
                          <Badge variant={q.has_answer ? "default" : "secondary"} className="shrink-0">
                            {q.has_answer ? "答弁あり" : "未答弁"}
                          </Badge>
                        </div>
                        {(q.question_url || q.answer_url) && (
                          <div className="flex gap-3 mt-2">
                            {q.question_url && (
                              <a href={q.question_url} target="_blank" rel="noopener noreferrer" className="text-xs text-blue-600 hover:underline">
                                質問本文
                              </a>
                            )}
                            {q.answer_url && (
                              <a href={q.answer_url} target="_blank" rel="noopener noreferrer" className="text-xs text-blue-600 hover:underline">
                                答弁書
                              </a>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                  <Pagination page={wqPage} pages={wqPages} onPageChange={setWqPage} />
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="user-reviews">
          <UserReviewSection memberId={memberId} aiScores={latestScore} />
        </TabsContent>
      </Tabs>

      {/* 同じ選挙区の議員 */}
      {sameDistrictMembers.length > 0 && member.district && (
        <Card className="mt-8">
          <CardHeader>
            <CardTitle className="text-base">「{member.district}」の他の議員</CardTitle>
            <p className="text-xs text-muted-foreground">同じ選挙区の議員をスコア順に表示しています</p>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {sameDistrictMembers.map((m) => {
                const s = m.latest_score;
                const gc = s ? (GRADE_COLORS[s.grade] || "bg-gray-300") : "bg-gray-300";
                return (
                  <Link key={m.id} href={`/members/${m.id}`}>
                    <div className="rounded-lg border p-3 hover:bg-muted/50 transition-colors cursor-pointer">
                      <div className="flex items-center gap-3">
                        <span className={`inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-white text-xs font-bold ${gc}`}>
                          {s?.grade ?? "-"}
                        </span>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-blue-600 truncate">{m.name}</p>
                          <p className="text-xs text-muted-foreground">{m.party ?? "無所属"}</p>
                        </div>
                        {s && <span className="text-sm font-bold">{s.total.toFixed(1)}</span>}
                      </div>
                    </div>
                  </Link>
                );
              })}
            </div>
            <div className="mt-3 flex items-center justify-between">
              {sameDistrictMembers.length >= 1 && (
                <Link
                  href={`/compare?ids=${[memberId, ...sameDistrictMembers.slice(0, 3).map((m) => m.id)].join(",")}`}
                  className="text-xs text-blue-600 hover:underline"
                >
                  この選挙区の議員を比較 →
                </Link>
              )}
              <Link href={`/members?district=${encodeURIComponent(member.district)}&sort_by=total&sort_order=desc`} className="text-xs text-blue-600 hover:underline">
                全議員を見る →
              </Link>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
