"use client";

import { useState, useEffect, useCallback } from "react";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Pagination } from "@/components/ui/pagination";
import { LoadingSpinner } from "@/components/ui/loading";
import { ErrorMessage } from "@/components/ui/error";
import { BillList } from "@/components/bill/BillList";
import { getBills } from "@/lib/api";
import type { Bill } from "@/lib/types";

export default function BillsPage() {
  const [search, setSearch] = useState("");
  const [billKind, setBillKind] = useState("all");
  const [status, setStatus] = useState("all");
  const [page, setPage] = useState(1);
  const [bills, setBills] = useState<Bill[]>([]);
  const [total, setTotal] = useState(0);
  const [pages, setPages] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const perPage = 20;

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getBills({
        search: search || undefined,
        bill_kind: billKind === "all" ? undefined : billKind,
        status: status === "all" ? undefined : status,
        page,
        per_page: perPage,
      });
      setBills(res.items);
      setTotal(res.total);
      setPages(res.pages);
    } catch (e) {
      setError(e instanceof Error ? e.message : "データの取得に失敗しました");
    } finally {
      setLoading(false);
    }
  }, [search, billKind, status, page]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // フィルタ変更時にページをリセット
  useEffect(() => {
    setPage(1);
  }, [search, billKind, status]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <h1 className="text-2xl font-bold text-slate-800 mb-6">法案一覧</h1>

      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <Input
          placeholder="法案名で検索..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="sm:max-w-xs"
        />
        <Select value={billKind} onValueChange={setBillKind}>
          <SelectTrigger className="sm:w-40">
            <SelectValue placeholder="種別" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全種別</SelectItem>
            <SelectItem value="閣法">閣法</SelectItem>
            <SelectItem value="衆法">衆法</SelectItem>
            <SelectItem value="参法">参法</SelectItem>
          </SelectContent>
        </Select>
        <Select value={status} onValueChange={setStatus}>
          <SelectTrigger className="sm:w-40">
            <SelectValue placeholder="状態" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全状態</SelectItem>
            <SelectItem value="成立">成立</SelectItem>
            <SelectItem value="審議中">審議中</SelectItem>
            <SelectItem value="否決">否決</SelectItem>
            <SelectItem value="廃案">廃案</SelectItem>
            <SelectItem value="継続">継続</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <p className="text-sm text-slate-500 mb-4">{total}件の法案</p>

      {loading ? (
        <LoadingSpinner />
      ) : error ? (
        <ErrorMessage message={error} onRetry={fetchData} />
      ) : (
        <>
          <BillList bills={bills} />
          <Pagination page={page} pages={pages} onPageChange={setPage} />
        </>
      )}
    </div>
  );
}
