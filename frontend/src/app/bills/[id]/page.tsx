"use client";

import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { BillVoteResult } from "@/components/bill/BillVoteResult";
import { getMockBillDetail } from "@/lib/mock-data";

export default function BillDetailPage() {
  const bill = getMockBillDetail();

  const statusColors: Record<string, string> = {
    成立: "bg-emerald-100 text-emerald-800",
    否決: "bg-red-100 text-red-800",
    審議中: "bg-yellow-100 text-yellow-800",
  };
  const statusClass = statusColors[bill.status ?? ""] ?? "bg-slate-100 text-slate-600";

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      {/* パンくず */}
      <nav className="text-sm text-slate-500 mb-6">
        <Link href="/bills" className="hover:text-blue-600">法案一覧</Link>
        <span className="mx-2">/</span>
        <span className="text-slate-800">法案詳細</span>
      </nav>

      {/* 法案情報 */}
      <Card className="mb-6">
        <CardHeader>
          <div className="flex items-start justify-between gap-4">
            <CardTitle className="text-lg">{bill.title}</CardTitle>
            {bill.status && (
              <Badge className={statusClass}>{bill.status}</Badge>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <p className="text-slate-500">種別</p>
              <p className="font-medium">{bill.bill_kind}</p>
            </div>
            <div>
              <p className="text-slate-500">番号</p>
              <p className="font-medium">{bill.bill_number ? `第${bill.bill_number}号` : "-"}</p>
            </div>
            <div>
              <p className="text-slate-500">提出者種別</p>
              <p className="font-medium">{bill.proposer_type === "cabinet" ? "内閣" : "議員"}</p>
            </div>
            <div>
              <p className="text-slate-500">結果</p>
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
      <h2 className="text-lg font-bold text-slate-800 mb-4">投票結果</h2>
      <BillVoteResult voteResults={bill.vote_results} />
    </div>
  );
}
