"use client";

import { useCallback, useMemo } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Pagination } from "@/components/ui/pagination";
import { LoadingSpinner } from "@/components/ui/loading";
import { ErrorMessage } from "@/components/ui/error";
import { BillList } from "@/components/bill/BillList";
import { useBills, useSessions } from "@/lib/hooks";
import { ShareButton } from "@/components/ShareButton";
import { STATUS_COLORS } from "@/lib/constants";

export default function BillsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const search = searchParams.get("search") || "";
  const billKind = searchParams.get("kind") || "all";
  const status = searchParams.get("status") || "all";
  const sessionParam = searchParams.get("session") || "";
  const page = Number(searchParams.get("page")) || 1;
  const perPage = 20;

  const { data: sessions } = useSessions();
  const sessionNumber = sessionParam ? Number(sessionParam) : undefined;

  const { data, error, isLoading, mutate } = useBills({
    search: search || undefined,
    bill_kind: billKind === "all" ? undefined : billKind,
    status: status === "all" ? undefined : status,
    session_number: sessionNumber,
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
  const setSession = useCallback(
    (v: string) => updateParams({ session: v === "all" ? undefined : v, page: undefined }),
    [updateParams],
  );
  const setPage = useCallback(
    (p: number) => updateParams({ page: p === 1 ? undefined : String(p) }),
    [updateParams],
  );

  // 法案種別ごとの件数 (全データ集計は表示中ページのみ)
  const kindCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const b of bills) {
      counts[b.bill_kind] = (counts[b.bill_kind] ?? 0) + 1;
    }
    return counts;
  }, [bills]);

  const enactedCount = useMemo(() => bills.filter((b) => b.status === "成立").length, [bills]);

  const statusCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const b of bills) {
      const s = b.status || "不明";
      counts[s] = (counts[s] ?? 0) + 1;
    }
    return counts;
  }, [bills]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <div className="flex items-center gap-3 mb-6">
        <h1 className="text-2xl font-bold text-foreground">法案一覧</h1>
        <ShareButton title="法案一覧 | GiinScore" />
      </div>

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
        {sessions && sessions.length > 0 && (
          <Select value={sessionParam || "all"} onValueChange={setSession}>
            <SelectTrigger className="sm:w-44">
              <SelectValue placeholder="会期" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全会期</SelectItem>
              {sessions.map((s) => (
                <SelectItem key={s.session_number} value={String(s.session_number)}>
                  第{s.session_number}回 ({s.kind})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </div>

      {/* 件数サマリー */}
      <div className="flex items-center gap-4 mb-4 flex-wrap">
        <p className="text-sm text-muted-foreground">{total}件の法案</p>
        {enactedCount > 0 && (
          <span className="text-xs text-emerald-600 font-medium">成立 {enactedCount}件</span>
        )}
        {Object.entries(kindCounts).map(([kind, count]) => (
          <span key={kind} className="text-xs text-muted-foreground">{kind}: {count}件</span>
        ))}
      </div>

      {/* ステータス分布バー */}
      {bills.length > 0 && Object.keys(statusCounts).length > 1 && (
        <div className="mb-6">
          <div className="flex h-4 rounded-full overflow-hidden">
            {Object.entries(statusCounts).map(([s, count]) => {
              const pct = (count / bills.length) * 100;
              const colorClass = STATUS_COLORS[s] ?? "bg-muted text-muted-foreground";
              return (
                <div
                  key={s}
                  className={`${colorClass} flex items-center justify-center text-[9px] font-medium`}
                  style={{ width: `${pct}%` }}
                  title={`${s}: ${count}件 (${pct.toFixed(0)}%)`}
                >
                  {pct >= 10 ? s : ""}
                </div>
              );
            })}
          </div>
          <div className="flex items-center gap-3 mt-1.5 text-xs text-muted-foreground flex-wrap">
            {Object.entries(statusCounts).map(([s, count]) => (
              <span key={s} className="flex items-center gap-1">
                <span className={`h-2 w-2 rounded-sm ${(STATUS_COLORS[s] ?? "bg-muted").split(" ")[0]}`} />
                {s} {count}
              </span>
            ))}
          </div>
        </div>
      )}

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
