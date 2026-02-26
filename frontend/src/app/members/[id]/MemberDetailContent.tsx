"use client";

import { useState, useMemo, use } from "react";
import Link from "next/link";
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
import { CHAMBER_LABELS, AXIS_LABELS } from "@/lib/types";
import { VOTE_LABELS, VOTE_COLORS } from "@/lib/constants";
import { useMember, useMemberSpeeches, useMemberVotes } from "@/lib/hooks";

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

  const [weights, setWeights] = useState({
    legislative_activity: 30,
    voting_behavior: 25,
    policy_influence: 25,
    transparency: 20,
  });

  const latestScore = member?.scores?.[0] ?? null;

  const customTotal = useMemo(() => {
    if (!latestScore) return 0;
    const sum = weights.legislative_activity + weights.voting_behavior + weights.policy_influence + weights.transparency;
    if (sum === 0) return 0;
    return (
      (latestScore.legislative_activity * weights.legislative_activity +
        latestScore.voting_behavior * weights.voting_behavior +
        latestScore.policy_influence * weights.policy_influence +
        latestScore.transparency * weights.transparency) / sum
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
      <nav aria-label="パンくずリスト" className="text-sm text-slate-500 mb-6">
        <Link href="/members" className="hover:text-blue-600">議員一覧</Link>
        <span className="mx-2">/</span>
        <span className="text-slate-800">{member.name}</span>
      </nav>

      {/* 議員情報ヘッダー */}
      <div className="flex flex-col md:flex-row gap-6 mb-8">
        <div className="flex items-start gap-4 flex-1">
          <div className="h-20 w-20 rounded-full bg-slate-200 flex items-center justify-center text-2xl font-bold text-slate-500">
            {member.name.charAt(0)}
          </div>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-slate-800">{member.name}</h1>
              <ShareButton title={shareTitle} url={shareUrl} />
            </div>
            {member.name_reading && <p className="text-sm text-slate-500">{member.name_reading}</p>}
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
                  />
                </CardContent>
              </Card>
            </div>
          </div>

          {/* 重みカスタマイズスライダー */}
          <Card className="mb-8">
            <CardHeader>
              <CardTitle className="text-base">スコアの重みカスタマイズ</CardTitle>
              <p className="text-xs text-slate-500">各軸の重みを調整して、あなた独自の評価基準でスコアを算出できます</p>
            </CardHeader>
            <CardContent className="space-y-4">
              {(Object.keys(weights) as Array<keyof typeof weights>).map((key) => (
                <div key={key} className="flex items-center gap-4">
                  <span className="text-sm text-slate-700 w-24">{AXIS_LABELS[key]}</span>
                  <Slider
                    value={[weights[key]]}
                    onValueChange={([v]) => setWeights((prev) => ({ ...prev, [key]: v }))}
                    max={100}
                    min={0}
                    step={5}
                    className="flex-1"
                  />
                  <span className="text-sm font-mono text-slate-600 w-12 text-right">{weights[key]}%</span>
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
          <CardContent className="p-6 text-center text-sm text-slate-500">
            スコアデータがまだ計算されていません
          </CardContent>
        </Card>
      )}

      {/* タブ: 発言・投票・法案 */}
      <Tabs defaultValue="speeches">
        <TabsList>
          <TabsTrigger value="speeches">発言履歴</TabsTrigger>
          <TabsTrigger value="votes">投票記録</TabsTrigger>
        </TabsList>

        <TabsContent value="speeches">
          <Card>
            <CardContent className="p-4">
              {speechLoading ? (
                <LoadingSpinner />
              ) : speeches.length === 0 ? (
                <p className="text-sm text-slate-500 text-center py-4">発言データがありません</p>
              ) : (
                <>
                  <table className="w-full">
                    <thead>
                      <tr className="border-b text-left text-xs text-slate-500">
                        <th scope="col" className="p-2">日付</th>
                        <th scope="col" className="p-2">会議名</th>
                        <th scope="col" className="p-2 text-right">文字数</th>
                      </tr>
                    </thead>
                    <tbody>
                      {speeches.map((s, i) => (
                        <tr key={i} className="border-b hover:bg-slate-50">
                          <td className="p-2 text-sm text-slate-600">
                            {s.speech_date ?? "-"}
                          </td>
                          <td className="p-2 text-sm">{s.meeting_name ?? "-"}</td>
                          <td className="p-2 text-sm text-right text-slate-600">
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

        <TabsContent value="votes">
          <Card>
            <CardContent className="p-4">
              {voteLoading ? (
                <LoadingSpinner />
              ) : votes.length === 0 ? (
                <p className="text-sm text-slate-500 text-center py-4">投票データがありません</p>
              ) : (
                <>
                  <table className="w-full">
                    <thead>
                      <tr className="border-b text-left text-xs text-slate-500">
                        <th scope="col" className="p-2">法案名</th>
                        <th scope="col" className="p-2 text-center">投票</th>
                      </tr>
                    </thead>
                    <tbody>
                      {votes.map((v) => (
                        <tr key={v.id} className="border-b hover:bg-slate-50">
                          <td className="p-2 text-sm">{v.bill_title ?? "-"}</td>
                          <td className="p-2 text-center">
                            <Badge className={VOTE_COLORS[v.vote] ?? "bg-slate-100"}>
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
      </Tabs>
    </div>
  );
}
