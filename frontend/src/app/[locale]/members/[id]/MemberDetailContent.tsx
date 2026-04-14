"use client";

import { useState, useMemo, use } from "react";
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
import { CHAMBER_LABELS, AXIS_LABELS } from "@/lib/types";
import { VOTE_LABELS, VOTE_COLORS } from "@/lib/constants";
import { useMember, useMemberSpeeches, useMemberVotes, useVotePattern, useSpeechQuality, useWrittenQuestions } from "@/lib/hooks";

interface MemberDetailContentProps {
  params: Promise<{ id: string }>;
}

export default function MemberDetailContent({ params }: MemberDetailContentProps) {
  const { id } = use(params);
  const memberId = Number(id);

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

  if (isLoading) return <div className="mx-auto max-w-7xl px-4 py-8"><LoadingSpinner /></div>;
  if (error) return <div className="mx-auto max-w-7xl px-4 py-8"><ErrorMessage message={error instanceof Error ? error.message : "データの取得に失敗しました"} onRetry={() => mutate()} /></div>;
  if (!member) return <div className="mx-auto max-w-7xl px-4 py-8">議員が見つかりません</div>;

  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://giinscore.jp";
  const shareUrl = `${siteUrl}/members/${memberId}`;
  const shareTitle = latestScore
    ? `${member.name}の国会活動スコア: 総合${latestScore.total.toFixed(1)}点（グレード${latestScore.grade}） | GiinScore`
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
            <div className="flex gap-2 mt-2">
              <Badge variant="outline">{CHAMBER_LABELS[member.chamber]}</Badge>
              <Badge variant="secondary">{member.party ?? "無所属"}</Badge>
              {member.district && <Badge variant="secondary">{member.district}</Badge>}
            </div>
          </div>
        </div>
      </div>

      {latestScore ? (
        <>
          {/* スコア概要 */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div>
              <ScoreCard total={customTotal} grade={customGrade} label="総合スコア" />
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
                </CardContent>
              </Card>
            </div>
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
      <Tabs defaultValue="speeches">
        <TabsList>
          <TabsTrigger value="speeches">発言履歴</TabsTrigger>
          <TabsTrigger value="speech-quality">質問品質</TabsTrigger>
          <TabsTrigger value="votes">投票記録</TabsTrigger>
          <TabsTrigger value="vote-pattern">投票パターン</TabsTrigger>
          <TabsTrigger value="written-questions">質問主意書</TabsTrigger>
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
                  {/* サマリーカード */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="rounded-lg border p-4 text-center">
                      <p className="text-xs text-muted-foreground">投票参加率</p>
                      <p className="text-2xl font-bold text-blue-600">{votePattern.participation_rate}%</p>
                      <p className="text-xs text-muted-foreground/70">{votePattern.total_votes}/{votePattern.total_votes + votePattern.absent_count}回</p>
                    </div>
                    <div className="rounded-lg border p-4 text-center">
                      <p className="text-xs text-muted-foreground">造反率</p>
                      <p className="text-2xl font-bold text-orange-600">{votePattern.dissent_rate}%</p>
                      <p className="text-xs text-muted-foreground/70">{votePattern.dissent_votes}/{votePattern.party_majority_votes}回</p>
                    </div>
                    <div className="rounded-lg border p-4 text-center">
                      <p className="text-xs text-muted-foreground">投票回数</p>
                      <p className="text-2xl font-bold text-foreground/80">{votePattern.total_votes}</p>
                    </div>
                    <div className="rounded-lg border p-4 text-center">
                      <p className="text-xs text-muted-foreground">欠席回数</p>
                      <p className="text-2xl font-bold text-muted-foreground/70">{votePattern.absent_count}</p>
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
      </Tabs>
    </div>
  );
}
