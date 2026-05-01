"use client";

import { useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LoadingSpinner } from "@/components/ui/loading";
import { ErrorMessage } from "@/components/ui/error";
import { useDataQuality, useLastUpdated } from "@/lib/hooks";

function ProgressBar({ value, max, color }: { value: number; max: number; color: string }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-muted-foreground tabular-nums w-10 text-right">
        {pct.toFixed(0)}%
      </span>
    </div>
  );
}

function CoverageLevel({ value }: { value: number }) {
  if (value >= 80) return <span className="text-xs font-medium text-emerald-600">充実</span>;
  if (value >= 50) return <span className="text-xs font-medium text-amber-600">中程度</span>;
  if (value > 0) return <span className="text-xs font-medium text-orange-500">不足</span>;
  return <span className="text-xs font-medium text-red-500">なし</span>;
}

export default function DataQualityContent() {
  const { data, error, isLoading, mutate } = useDataQuality();
  const { data: lastUpdated } = useLastUpdated();

  const aggregated = useMemo(() => {
    if (!data) return null;
    const sessions = data.sessions;
    const scoredSessions = sessions.filter((s) => s.scored_member_count > 0).length;
    const speechSessions = sessions.filter((s) => s.speech_count > 0).length;
    const billSessions = sessions.filter((s) => s.bill_count > 0).length;
    const voteSessions = sessions.filter((s) => s.vote_result_count > 0).length;
    const totalSpeeches = sessions.reduce((acc, s) => acc + s.speech_count, 0);
    const totalBills = sessions.reduce((acc, s) => acc + s.bill_count, 0);
    const totalVoteRecords = sessions.reduce((acc, s) => acc + s.vote_record_count, 0);
    const maxScoredMembers = Math.max(...sessions.map((s) => s.scored_member_count), 0);
    const maxSpeeches = Math.max(...sessions.map((s) => s.speech_count), 0);
    return {
      scoredSessions,
      speechSessions,
      billSessions,
      voteSessions,
      totalSpeeches,
      totalBills,
      totalVoteRecords,
      maxScoredMembers,
      maxSpeeches,
    };
  }, [data]);

  if (isLoading) return <div className="mx-auto max-w-7xl px-4 py-8"><LoadingSpinner /></div>;
  if (error) return <div className="mx-auto max-w-7xl px-4 py-8"><ErrorMessage message="データの取得に失敗しました" onRetry={() => mutate()} /></div>;
  if (!data || !aggregated) return null;

  const pipelineStatuses = lastUpdated?.pipelines ?? [];

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <h1 className="text-2xl font-bold text-foreground mb-2">データ品質ダッシュボード</h1>
      <p className="text-sm text-muted-foreground mb-8">
        会期ごとのデータ充足状況を一覧で確認できます
      </p>

      {/* サマリーカード */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
        <Card>
          <CardContent className="p-4 text-center">
            <p className="text-2xl font-bold text-foreground">{data.total_members.toLocaleString()}</p>
            <p className="text-xs text-muted-foreground">登録議員数</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <p className="text-2xl font-bold text-foreground">{data.total_sessions}</p>
            <p className="text-xs text-muted-foreground">登録会期数</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <p className="text-2xl font-bold text-foreground">{aggregated.totalSpeeches.toLocaleString()}</p>
            <p className="text-xs text-muted-foreground">総発言数</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <p className="text-2xl font-bold text-foreground">{aggregated.totalBills.toLocaleString()}</p>
            <p className="text-xs text-muted-foreground">総法案数</p>
          </CardContent>
        </Card>
      </div>

      {/* データカバレッジ概要 */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="text-base">データカバレッジ</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm">スコア算出済み会期</span>
              <span className="text-xs text-muted-foreground">{aggregated.scoredSessions} / {data.total_sessions}</span>
            </div>
            <ProgressBar value={aggregated.scoredSessions} max={data.total_sessions} color="bg-emerald-500" />
          </div>
          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm">発言データ取得済み会期</span>
              <span className="text-xs text-muted-foreground">{aggregated.speechSessions} / {data.total_sessions}</span>
            </div>
            <ProgressBar value={aggregated.speechSessions} max={data.total_sessions} color="bg-blue-500" />
          </div>
          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm">法案データ取得済み会期</span>
              <span className="text-xs text-muted-foreground">{aggregated.billSessions} / {data.total_sessions}</span>
            </div>
            <ProgressBar value={aggregated.billSessions} max={data.total_sessions} color="bg-violet-500" />
          </div>
          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm">投票データ取得済み会期</span>
              <span className="text-xs text-muted-foreground">{aggregated.voteSessions} / {data.total_sessions}</span>
            </div>
            <ProgressBar value={aggregated.voteSessions} max={data.total_sessions} color="bg-amber-500" />
          </div>
        </CardContent>
      </Card>

      {/* パイプライン実行状況 */}
      {pipelineStatuses.length > 0 && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="text-base">パイプライン実行状況</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b bg-muted/50 text-left text-xs text-muted-foreground">
                    <th scope="col" className="p-3">パイプライン</th>
                    <th scope="col" className="p-3">ステータス</th>
                    <th scope="col" className="p-3 text-right">処理件数</th>
                    <th scope="col" className="p-3">最終実行</th>
                  </tr>
                </thead>
                <tbody>
                  {pipelineStatuses.map((p) => (
                    <tr key={p.pipeline_name} className="border-b hover:bg-muted/50 transition-colors">
                      <td className="p-3 text-sm font-medium text-foreground">{p.pipeline_name}</td>
                      <td className="p-3">
                        <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                          p.status === "completed"
                            ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-400"
                            : p.status === "running"
                              ? "bg-blue-100 text-blue-700 dark:bg-blue-950/50 dark:text-blue-400"
                              : "bg-red-100 text-red-700 dark:bg-red-950/50 dark:text-red-400"
                        }`}>
                          {p.status}
                        </span>
                      </td>
                      <td className="p-3 text-right text-sm text-muted-foreground">
                        {p.records_processed.toLocaleString()}
                      </td>
                      <td className="p-3 text-sm text-muted-foreground">
                        {p.finished_at ? new Date(p.finished_at).toLocaleString("ja-JP") : "-"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 会期別テーブル */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">会期別データ充足状況</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-muted/50 text-left text-xs text-muted-foreground">
                  <th scope="col" className="p-3">会期</th>
                  <th scope="col" className="p-3">種別</th>
                  <th scope="col" className="p-3 text-right">スコア済</th>
                  <th scope="col" className="p-3 text-right">発言数</th>
                  <th scope="col" className="p-3 text-right hidden sm:table-cell">発言者</th>
                  <th scope="col" className="p-3 text-right">法案数</th>
                  <th scope="col" className="p-3 text-right hidden sm:table-cell">投票案件</th>
                  <th scope="col" className="p-3 text-right hidden sm:table-cell">投票レコード</th>
                  <th scope="col" className="p-3 text-center">充足度</th>
                </tr>
              </thead>
              <tbody>
                {data.sessions.map((s) => {
                  // 充足度スコア (0-100): scored + speeches + bills + votes の4要素
                  const hasScore = s.scored_member_count > 0 ? 25 : 0;
                  const hasSpeech = s.speech_count > 0 ? 25 : 0;
                  const hasBill = s.bill_count > 0 ? 25 : 0;
                  const hasVote = s.vote_result_count > 0 ? 25 : 0;
                  const coverage = hasScore + hasSpeech + hasBill + hasVote;
                  return (
                    <tr key={s.session_number} className="border-b hover:bg-muted/50 transition-colors">
                      <td className="p-3 text-sm font-medium text-foreground">第{s.session_number}回</td>
                      <td className="p-3 text-sm text-muted-foreground">{s.session_kind}</td>
                      <td className="p-3 text-right text-sm">
                        <span className={s.scored_member_count > 0 ? "text-emerald-600" : "text-muted-foreground/70"}>
                          {s.scored_member_count.toLocaleString()}
                        </span>
                      </td>
                      <td className="p-3 text-right text-sm">
                        <span className={s.speech_count > 0 ? "text-foreground" : "text-muted-foreground/70"}>
                          {s.speech_count.toLocaleString()}
                        </span>
                      </td>
                      <td className="p-3 text-right text-sm text-muted-foreground hidden sm:table-cell">{s.speakers_count.toLocaleString()}</td>
                      <td className="p-3 text-right text-sm">
                        <span className={s.bill_count > 0 ? "text-foreground" : "text-muted-foreground/70"}>
                          {s.bill_count.toLocaleString()}
                        </span>
                      </td>
                      <td className="p-3 text-right text-sm text-muted-foreground hidden sm:table-cell">{s.vote_result_count.toLocaleString()}</td>
                      <td className="p-3 text-right text-sm text-muted-foreground hidden sm:table-cell">{s.vote_record_count.toLocaleString()}</td>
                      <td className="p-3 text-center">
                        <CoverageLevel value={coverage} />
                      </td>
                    </tr>
                  );
                })}
                {data.sessions.length === 0 && (
                  <tr>
                    <td colSpan={9} className="p-8 text-center text-sm text-muted-foreground">
                      会期データがありません
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
