"use client";

import { useCallback } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Pagination } from "@/components/ui/pagination";
import { LoadingSpinner } from "@/components/ui/loading";
import { ErrorMessage } from "@/components/ui/error";
import { BillList } from "@/components/bill/BillList";
import { useBills } from "@/lib/hooks";

export default function BillsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const search = searchParams.get("search") || "";
  const billKind = searchParams.get("kind") || "all";
  const status = searchParams.get("status") || "all";
  const page = Number(searchParams.get("page")) || 1;
  const perPage = 20;

  const { data, error, isLoading, mutate } = useBills({
    search: search || undefined,
    bill_kind: billKind === "all" ? undefined : billKind,
    status: status === "all" ? undefined : status,
    page,
    per_page: perPage,
  });

  const bills = data?.items ?? [];
  const total = data?.total ?? 0;
  const pages = data?.pages ?? 0;

  const updateParams = useCallback(
    (updates: Record<string, string | undefined>) => {
      const params = new URLSearchParams(searchParams.toString());
      Object.entries(updates).forEach(([key, value]) => {
        if (value === undefined || value === "" || value === "all") {
          params.delete(key);
        } else {
          params.set(key, value);
        }
      });
      const qs = params.toString();
      router.push(qs ? `/bills?${qs}` : "/bills");
    },
    [router, searchParams],
  );

  const setSearch = useCallback(
    (v: string) => updateParams({ search: v, page: undefined }),
    [updateParams],
  );
  const setBillKind = useCallback(
    (v: string) => updateParams({ kind: v, page: undefined }),
    [updateParams],
  );
  const setStatus = useCallback(
    (v: string) => updateParams({ status: v, page: undefined }),
    [updateParams],
  );
  const setPage = useCallback(
    (p: number) => updateParams({ page: p === 1 ? undefined : String(p) }),
    [updateParams],
  );

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <h1 className="text-2xl font-bold text-foreground mb-6">法案一覧</h1>

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

      <p className="text-sm text-muted-foreground mb-4">{total}件の法案</p>

      {isLoading ? (
        <LoadingSpinner />
      ) : error ? (
        <ErrorMessage
          message={error instanceof Error ? error.message : "データの取得に失敗しました"}
          onRetry={() => mutate()}
        />
      ) : (
        <>
          <BillList bills={bills} />
          <Pagination page={page} pages={pages} onPageChange={setPage} />
        </>
      )}
    </div>
  );
}
