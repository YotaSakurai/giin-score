"use client";

import { useCallback } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { MemberList } from "@/components/member/MemberList";
import { MemberFilter } from "@/components/member/MemberFilter";
import { Pagination } from "@/components/ui/pagination";
import { LoadingSpinner } from "@/components/ui/loading";
import { ErrorMessage } from "@/components/ui/error";
import { useMembers } from "@/lib/hooks";

export default function MembersContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const search = searchParams.get("search") || "";
  const chamber = searchParams.get("chamber") || "all";
  const party = searchParams.get("party") || "all";
  const district = searchParams.get("district") || "";
  const page = Number(searchParams.get("page")) || 1;
  const perPage = 20;

  const { data, error, isLoading, mutate } = useMembers({
    search: search || undefined,
    chamber: chamber === "all" ? undefined : chamber,
    party: party === "all" ? undefined : party,
    district: district || undefined,
    page,
    per_page: perPage,
  });

  const members = data?.items ?? [];
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
      router.push(qs ? `/members?${qs}` : "/members");
    },
    [router, searchParams],
  );

  const setSearch = useCallback(
    (v: string) => updateParams({ search: v, page: undefined }),
    [updateParams],
  );
  const setChamber = useCallback(
    (v: string) => updateParams({ chamber: v, page: undefined }),
    [updateParams],
  );
  const setParty = useCallback(
    (v: string) => updateParams({ party: v, page: undefined }),
    [updateParams],
  );
  const setDistrict = useCallback(
    (v: string) => updateParams({ district: v, page: undefined }),
    [updateParams],
  );
  const setPage = useCallback(
    (p: number) => updateParams({ page: p === 1 ? undefined : String(p) }),
    [updateParams],
  );

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <h1 className="text-2xl font-bold text-slate-800 mb-6">議員一覧</h1>
      <MemberFilter
        search={search}
        chamber={chamber}
        party={party}
        district={district}
        onSearchChange={setSearch}
        onChamberChange={setChamber}
        onPartyChange={setParty}
        onDistrictChange={setDistrict}
      />
      <p className="text-sm text-slate-500 mb-4">{total}名の議員</p>

      {isLoading ? (
        <LoadingSpinner />
      ) : error ? (
        <ErrorMessage
          message={error instanceof Error ? error.message : "データの取得に失敗しました"}
          onRetry={() => mutate()}
        />
      ) : (
        <>
          <MemberList members={members} />
          <Pagination page={page} pages={pages} onPageChange={setPage} />
        </>
      )}
    </div>
  );
}
