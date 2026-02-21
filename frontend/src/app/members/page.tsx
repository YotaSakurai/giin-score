"use client";

import { useState, useEffect, useCallback } from "react";
import { MemberList } from "@/components/member/MemberList";
import { MemberFilter } from "@/components/member/MemberFilter";
import { Pagination } from "@/components/ui/pagination";
import { LoadingSpinner } from "@/components/ui/loading";
import { ErrorMessage } from "@/components/ui/error";
import { getMembers } from "@/lib/api";
import type { MemberWithScore } from "@/lib/types";

export default function MembersPage() {
  const [search, setSearch] = useState("");
  const [chamber, setChamber] = useState("all");
  const [party, setParty] = useState("all");
  const [page, setPage] = useState(1);
  const [members, setMembers] = useState<MemberWithScore[]>([]);
  const [total, setTotal] = useState(0);
  const [pages, setPages] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const perPage = 20;

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getMembers({
        search: search || undefined,
        chamber: chamber === "all" ? undefined : chamber,
        party: party === "all" ? undefined : party,
        page,
        per_page: perPage,
      });
      setMembers(res.items);
      setTotal(res.total);
      setPages(res.pages);
    } catch (e) {
      setError(e instanceof Error ? e.message : "データの取得に失敗しました");
    } finally {
      setLoading(false);
    }
  }, [search, chamber, party, page]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // フィルタ変更時にページをリセット
  useEffect(() => {
    setPage(1);
  }, [search, chamber, party]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <h1 className="text-2xl font-bold text-slate-800 mb-6">議員一覧</h1>
      <MemberFilter
        search={search}
        chamber={chamber}
        party={party}
        onSearchChange={setSearch}
        onChamberChange={setChamber}
        onPartyChange={setParty}
      />
      <p className="text-sm text-slate-500 mb-4">{total}名の議員</p>

      {loading ? (
        <LoadingSpinner />
      ) : error ? (
        <ErrorMessage message={error} onRetry={fetchData} />
      ) : (
        <>
          <MemberList members={members} />
          <Pagination page={page} pages={pages} onPageChange={setPage} />
        </>
      )}
    </div>
  );
}
