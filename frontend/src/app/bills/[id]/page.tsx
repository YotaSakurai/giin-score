"use client";

import { useState, useEffect, useCallback, use } from "react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { LoadingSpinner } from "@/components/ui/loading";
import { ErrorMessage } from "@/components/ui/error";
import { BillVoteResult } from "@/components/bill/BillVoteResult";
import { getBill } from "@/lib/api";
import type { BillDetail } from "@/lib/types";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function BillDetailPage({ params }: PageProps) {
  const { id } = use(params);
  const billId = Number(id);

  const [bill, setBill] = useState<BillDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchBill = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getBill(billId);
      setBill(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "データの取得に失敗しました");
    } finally {
      setLoading(false);
    }
  }, [billId]);

  useEffect(() => {
    fetchBill();
  }, [fetchBill]);

  if (loading) return <div className="mx-auto max-w-7xl px-4 py-8"><LoadingSpinner /></div>;
  if (error) return <div className="mx-auto max-w-7xl px-4 py-8"><ErrorMessage message={error} onRetry={fetchBill} /></div>;
  if (!bill) return <div className="mx-auto max-w-7xl px-4 py-8">法案が見つかりません</div>;

  const statusColors: Record<string, string> = {
    成立: "bg-emerald-100 text-emerald-800",
    否決: "bg-red-100 text-red-800",
    審議中: "bg-yellow-100 text-yellow-800",
    廃案: "bg-red-100 text-red-800",
    継続: "bg-blue-100 text-blue-800",
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
      {bill.vote_results.length > 0 && (
        <>
          <h2 className="text-lg font-bold text-slate-800 mb-4">投票結果</h2>
          <BillVoteResult voteResults={bill.vote_results} />
        </>
      )}
    </div>
  );
}
