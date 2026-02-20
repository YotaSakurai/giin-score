"use client";

import { useState, useMemo, use } from "react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Slider } from "@/components/ui/slider";
import { ScoreRadarChart } from "@/components/score/ScoreRadarChart";
import { ScoreCard } from "@/components/score/ScoreCard";
import { ScoreBreakdown } from "@/components/score/ScoreBreakdown";
import { CHAMBER_LABELS, AXIS_LABELS } from "@/lib/types";
import { getMockMemberDetail } from "@/lib/mock-data";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function MemberDetailPage({ params }: PageProps) {
  const { id } = use(params);
  const member = getMockMemberDetail(Number(id));
  const latestScore = member.scores[0];

  const [weights, setWeights] = useState({
    legislative_activity: 30,
    voting_behavior: 25,
    policy_influence: 25,
    transparency: 20,
  });

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

  if (!latestScore) {
    return <div className="mx-auto max-w-7xl px-4 py-8">スコアデータがありません</div>;
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      {/* パンくず */}
      <nav className="text-sm text-slate-500 mb-6">
        <Link href="/members" className="hover:text-blue-600">議員一覧</Link>
        <span className="mx-2">/</span>
        <span className="text-slate-800">{member.name}</span>
      </nav>

      {/* 議員情報ヘッダー */}
      <div className="flex flex-col md:flex-row gap-6 mb-8">
        <div className="flex items-start gap-4">
          <div className="h-20 w-20 rounded-full bg-slate-200 flex items-center justify-center text-2xl font-bold text-slate-500">
            {member.name.charAt(0)}
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-800">{member.name}</h1>
            {member.name_reading && <p className="text-sm text-slate-500">{member.name_reading}</p>}
            <div className="flex gap-2 mt-2">
              <Badge variant="outline">{CHAMBER_LABELS[member.chamber]}</Badge>
              <Badge variant="secondary">{member.party ?? "無所属"}</Badge>
              {member.district && <Badge variant="secondary">{member.district}</Badge>}
            </div>
          </div>
        </div>
      </div>

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
          breakdown={latestScore.breakdown as Record<string, unknown>}
          scores={{
            legislative_activity: latestScore.legislative_activity,
            voting_behavior: latestScore.voting_behavior,
            policy_influence: latestScore.policy_influence,
            transparency: latestScore.transparency,
          }}
        />
      </div>

      {/* タブ: 発言・投票・法案 */}
      <Tabs defaultValue="speeches">
        <TabsList>
          <TabsTrigger value="speeches">発言履歴</TabsTrigger>
          <TabsTrigger value="votes">投票記録</TabsTrigger>
          <TabsTrigger value="bills">法案関与</TabsTrigger>
        </TabsList>
        <TabsContent value="speeches">
          <Card>
            <CardContent className="p-4">
              <p className="text-sm text-slate-500">
                発言データはバックエンドAPI接続後に表示されます。
                この議員は第213回国会で計{(latestScore.breakdown as Record<string, Record<string, number>>)?.legislative_activity?.speech_count ?? 0}回の発言を行いました。
              </p>
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="votes">
          <Card>
            <CardContent className="p-4">
              <p className="text-sm text-slate-500">
                投票データはバックエンドAPI接続後に表示されます。
                投票参加率: {(latestScore.breakdown as Record<string, Record<string, number>>)?.voting_behavior?.participation_rate ?? 0}%
              </p>
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="bills">
          <Card>
            <CardContent className="p-4">
              <p className="text-sm text-slate-500">
                法案データはバックエンドAPI接続後に表示されます。
                成立法案数: {(latestScore.breakdown as Record<string, Record<string, number>>)?.policy_influence?.enacted_count ?? 0}件
              </p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
