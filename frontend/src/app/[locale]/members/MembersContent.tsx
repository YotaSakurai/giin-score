"use client";

import { useCallback, useMemo } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { MemberList } from "@/components/member/MemberList";
import { Pagination } from "@/components/ui/pagination";
import { LoadingSpinner } from "@/components/ui/loading";
import { ErrorMessage } from "@/components/ui/error";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useMembers, useMembersScatter } from "@/lib/hooks";
import { AdvancedMemberFilter, type AdvancedFilterState } from "@/components/member/AdvancedMemberFilter";
import { ViewModeToggle, type ViewMode } from "@/components/member/ViewModeToggle";
import { MemberTable } from "@/components/member/MemberTable";
import { MemberScatterPlot } from "@/components/member/MemberScatterPlot";

function parseRange(minStr: string | null, maxStr: string | null): [number, number] {
  const min = minStr ? Number(minStr) : 0;
  const max = maxStr ? Number(maxStr) : 100;
  return [min, max];
}

function isRangeActive(range: [number, number]): boolean {
  return range[0] > 0 || range[1] < 100;
}

function rangeParams(range: [number, number], minKey: string, maxKey: string): Record<string, number | undefined> {
  return {
    [minKey]: range[0] > 0 ? range[0] : undefined,
    [maxKey]: range[1] < 100 ? range[1] : undefined,
  };
}

export default function MembersContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // URL→状態パース
  const filterState: AdvancedFilterState = useMemo(() => {
    const gradeStr = searchParams.get("grade");
    return {
      search: searchParams.get("search") || "",
      chamber: searchParams.get("chamber") || "all",
      party: searchParams.get("party") || "all",
      district: searchParams.get("district") || "",
      grades: gradeStr ? gradeStr.split(",") : [],
      scoreRange: parseRange(searchParams.get("score_min"), searchParams.get("score_max")),
      laRange: parseRange(searchParams.get("la_min"), searchParams.get("la_max")),
      vbRange: parseRange(searchParams.get("vb_min"), searchParams.get("vb_max")),
      piRange: parseRange(searchParams.get("pi_min"), searchParams.get("pi_max")),
      trRange: parseRange(searchParams.get("tr_min"), searchParams.get("tr_max")),
      qqRange: parseRange(searchParams.get("qq_min"), searchParams.get("qq_max")),
    };
  }, [searchParams]);

  const viewMode = (searchParams.get("view") as ViewMode) || "grid";
  const page = Number(searchParams.get("page")) || 1;
  const sortBy = searchParams.get("sort_by") || "name";
  const sortOrder = (searchParams.get("sort_order") as "asc" | "desc") || "desc";
  const scatterX = searchParams.get("sx") || "legislative_activity";
  const scatterY = searchParams.get("sy") || "question_quality";
  const scatterColor = (searchParams.get("sc") || "party") as "party" | "grade" | "chamber";
  const perPage = Number(searchParams.get("per_page")) || 20;

  // URLパラメータ更新
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

  // フィルタ状態→APIパラメータ変換
  const apiFilterParams = useMemo(() => {
    const s = filterState;
    return {
      search: s.search || undefined,
      chamber: s.chamber === "all" ? undefined : s.chamber,
      party: s.party === "all" ? undefined : s.party,
      district: s.district || undefined,
      grade: s.grades.length > 0 ? s.grades.join(",") : undefined,
      ...rangeParams(s.scoreRange, "score_min", "score_max"),
      ...rangeParams(s.laRange, "la_min", "la_max"),
      ...rangeParams(s.vbRange, "vb_min", "vb_max"),
      ...rangeParams(s.piRange, "pi_min", "pi_max"),
      ...rangeParams(s.trRange, "tr_min", "tr_max"),
      ...rangeParams(s.qqRange, "qq_min", "qq_max"),
    };
  }, [filterState]);

  // データ取得
  const isScatterView = viewMode === "scatter";
  const membersResult = useMembers(
    isScatterView
      ? undefined
      : { ...apiFilterParams, sort_by: sortBy, sort_order: sortOrder, page, per_page: perPage },
  );
  const scatterResult = useMembersScatter(isScatterView ? apiFilterParams : undefined);

  const members = membersResult.data?.items ?? [];
  const total = membersResult.data?.total ?? 0;
  const pages = membersResult.data?.pages ?? 0;
  const scatterData = scatterResult.data ?? [];

  const isLoading = isScatterView ? scatterResult.isLoading : membersResult.isLoading;
  const error = isScatterView ? scatterResult.error : membersResult.error;
  const mutate = isScatterView ? scatterResult.mutate : membersResult.mutate;

  // フィルタ変更ハンドラ
  const handleFilterChange = useCallback(
    (newState: AdvancedFilterState) => {
      const updates: Record<string, string | undefined> = {
        search: newState.search || undefined,
        chamber: newState.chamber,
        party: newState.party,
        district: newState.district || undefined,
        grade: newState.grades.length > 0 ? newState.grades.join(",") : undefined,
        page: undefined, // ページリセット
      };

      // レンジパラメータ
      const ranges: [string, string, [number, number]][] = [
        ["score_min", "score_max", newState.scoreRange],
        ["la_min", "la_max", newState.laRange],
        ["vb_min", "vb_max", newState.vbRange],
        ["pi_min", "pi_max", newState.piRange],
        ["tr_min", "tr_max", newState.trRange],
        ["qq_min", "qq_max", newState.qqRange],
      ];
      for (const [minKey, maxKey, range] of ranges) {
        updates[minKey] = isRangeActive(range) && range[0] > 0 ? String(range[0]) : undefined;
        updates[maxKey] = isRangeActive(range) && range[1] < 100 ? String(range[1]) : undefined;
      }

      updateParams(updates);
    },
    [updateParams],
  );

  const handleViewChange = useCallback(
    (mode: ViewMode) => updateParams({ view: mode === "grid" ? undefined : mode, page: undefined }),
    [updateParams],
  );

  const handleSortChange = useCallback(
    (newSortBy: string, newSortOrder: "asc" | "desc") => {
      updateParams({ sort_by: newSortBy === "name" ? undefined : newSortBy, sort_order: newSortOrder === "desc" ? undefined : newSortOrder, page: undefined });
    },
    [updateParams],
  );

  const setPage = useCallback(
    (p: number) => updateParams({ page: p === 1 ? undefined : String(p) }),
    [updateParams],
  );

  const setPerPage = useCallback(
    (v: string) => updateParams({ per_page: v === "20" ? undefined : v, page: undefined }),
    [updateParams],
  );

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-foreground">議員一覧</h1>
        <ViewModeToggle value={viewMode} onChange={handleViewChange} />
      </div>

      <AdvancedMemberFilter state={filterState} onChange={handleFilterChange} />

      {!isScatterView && (
        <p className="text-sm text-muted-foreground mb-4">{total}名の議員</p>
      )}
      {isScatterView && (
        <p className="text-sm text-muted-foreground mb-4">{scatterData.length}名の議員</p>
      )}

      {isLoading ? (
        <LoadingSpinner />
      ) : error ? (
        <ErrorMessage
          message={error instanceof Error ? error.message : "データの取得に失敗しました"}
          onRetry={() => mutate()}
        />
      ) : viewMode === "grid" ? (
        <>
          <MemberList members={members} />
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <Pagination page={page} pages={pages} onPageChange={setPage} />
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-muted-foreground">表示件数:</span>
              <Select value={String(perPage)} onValueChange={setPerPage}>
                <SelectTrigger className="w-20 h-8 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="20">20</SelectItem>
                  <SelectItem value="50">50</SelectItem>
                  <SelectItem value="100">100</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </>
      ) : viewMode === "table" ? (
        <>
          <MemberTable
            members={members}
            sortBy={sortBy}
            sortOrder={sortOrder}
            onSortChange={handleSortChange}
          />
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <Pagination page={page} pages={pages} onPageChange={setPage} />
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-muted-foreground">表示件数:</span>
              <Select value={String(perPage)} onValueChange={setPerPage}>
                <SelectTrigger className="w-20 h-8 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="20">20</SelectItem>
                  <SelectItem value="50">50</SelectItem>
                  <SelectItem value="100">100</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </>
      ) : (
        <MemberScatterPlot
          data={scatterData}
          xAxis={scatterX}
          yAxis={scatterY}
          colorBy={scatterColor}
          onXAxisChange={(v) => updateParams({ sx: v === "legislative_activity" ? undefined : v })}
          onYAxisChange={(v) => updateParams({ sy: v === "question_quality" ? undefined : v })}
          onColorByChange={(v) => updateParams({ sc: v === "party" ? undefined : v })}
        />
      )}
    </div>
  );
}
