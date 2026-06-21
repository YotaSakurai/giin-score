"use client";

import { use } from "react";
import { Link } from "@/i18n/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { LoadingSpinner } from "@/components/ui/loading";
import { ErrorMessage } from "@/components/ui/error";
import { BillVoteResult } from "@/components/bill/BillVoteResult";
import { STATUS_COLORS } from "@/lib/constants";
import { useBill } from "@/lib/hooks";
import { ShareButton } from "@/components/ShareButton";
import { Breadcrumb } from "@/components/layout/Breadcrumb";

interface Props {
  params: Promise<{ id: string }>;
}

export default function BillDetailContent({ params }: Props) {
  const { id } = use(params);
  const billId = Number(id);

  const { data: bill, error, isLoading, mutate } = useBill(billId);

  if (isLoading) return <div className="mx-auto max-w-7xl px-4 py-8"><LoadingSpinner /></div>;
  if (error) return <div className="mx-auto max-w-7xl px-4 py-8"><ErrorMessage message={error instanceof Error ? error.message : "データの取得に失敗しました"} onRetry={() => mutate()} /></div>;
  if (!bill) return <div className="mx-auto max-w-7xl px-4 py-8">法案が見つかりません</div>;

  const statusClass = STATUS_COLORS[bill.status ?? ""] ?? "bg-muted text-muted-foreground";

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <Breadcrumb items={[
        { label: "法案一覧", href: "/bills" },
        { label: bill.title || "法案詳細" },
      ]} />

      {/* 法案情報 */}
      <Card className="mb-6">
        <CardHeader>
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-3 flex-1 min-w-0">
              <CardTitle className="text-lg">{bill.title}</CardTitle>
              <ShareButton title={`${bill.title} | GiinScore法案詳細`} />
            </div>
            {bill.status && (
              <Badge className={statusClass}>{bill.status}</Badge>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <p className="text-muted-foreground">種別</p>
              <p className="font-medium">{bill.bill_kind}</p>
            </div>
            <div>
              <p className="text-muted-foreground">番号</p>
              <p className="font-medium">{bill.bill_number ? `第${bill.bill_number}号` : "-"}</p>
            </div>
            <div>
              <p className="text-muted-foreground">提出者種別</p>
              <p className="font-medium">{bill.proposer_type === "cabinet" ? "内閣" : "議員"}</p>
            </div>
            <div>
              <p className="text-muted-foreground">結果</p>
              <p className="font-medium">{bill.result ?? "未定"}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 提出者 */}
      {bill.sponsors.length > 0 && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="text-base">提出者</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {bill.sponsors.map((s) => (
                <Link key={s.member_id} href={`/members/${s.member_id}`}>
                  <Badge variant={s.sponsor_type === "primary" ? "default" : "secondary"} className="cursor-pointer hover:opacity-80">
                    {s.member_name}
                    {s.sponsor_type === "primary" && " (筆頭)"}
                  </Badge>
                </Link>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* 投票結果 */}
      {bill.vote_results.length > 0 && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="text-base">投票結果</CardTitle>
            <p className="text-xs text-muted-foreground">各議院での投票結果</p>
          </CardHeader>
          <CardContent>
            <BillVoteResult voteResults={bill.vote_results} />
          </CardContent>
        </Card>
      )}
    </div>
  );
}
