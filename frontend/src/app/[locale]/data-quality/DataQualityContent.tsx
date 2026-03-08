"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LoadingSpinner } from "@/components/ui/loading";
import { ErrorMessage } from "@/components/ui/error";
import { useDataQuality } from "@/lib/hooks";

export default function DataQualityContent() {
  const { data, error, isLoading, mutate } = useDataQuality();

  if (isLoading) return <div className="mx-auto max-w-7xl px-4 py-8"><LoadingSpinner /></div>;
  if (error) return <div className="mx-auto max-w-7xl px-4 py-8"><ErrorMessage message="データの取得に失敗しました" onRetry={() => mutate()} /></div>;
  if (!data) return null;

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <h1 className="text-2xl font-bold text-foreground mb-2">データ品質ダッシュボード</h1>
      <p className="text-sm text-muted-foreground mb-8">
        会期ごとのデータ充足状況を一覧で確認できます
      </p>

      {/* サマリー */}
      <div className="grid grid-cols-2 gap-4 mb-8">
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
      </div>

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
                  <th scope="col" className="p-3 text-right">発言者</th>
                  <th scope="col" className="p-3 text-right">法案数</th>
                  <th scope="col" className="p-3 text-right">投票案件</th>
                  <th scope="col" className="p-3 text-right">投票レコード</th>
                </tr>
              </thead>
              <tbody>
                {data.sessions.map((s) => (
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
                    <td className="p-3 text-right text-sm text-muted-foreground">{s.speakers_count.toLocaleString()}</td>
                    <td className="p-3 text-right text-sm">
                      <span className={s.bill_count > 0 ? "text-foreground" : "text-muted-foreground/70"}>
                        {s.bill_count.toLocaleString()}
                      </span>
                    </td>
                    <td className="p-3 text-right text-sm text-muted-foreground">{s.vote_result_count.toLocaleString()}</td>
                    <td className="p-3 text-right text-sm text-muted-foreground">{s.vote_record_count.toLocaleString()}</td>
                  </tr>
                ))}
                {data.sessions.length === 0 && (
                  <tr>
                    <td colSpan={8} className="p-8 text-center text-sm text-muted-foreground">
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
