"use client";

import { useCallback, useMemo } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { MemberList } from "@/components/member/MemberList";
import { Pagination } from "@/components/ui/pagination";
import { LoadingSpinner } from "@/components/ui/loading";
import { ErrorMessage } from "@/components/ui/error";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useMembers, useMembersScatter } from "@/lib/hooks";
import { CHAMBER_LABELS, AXIS_LABELS } from "@/lib/types";
import { AdvancedMemberFilter, type AdvancedFilterState } from "@/components/member/AdvancedMemberFilter";
import { ViewModeToggle, type ViewMode } from "@/components/member/ViewModeToggle";
import dynamic from "next/dynamic";

const MemberTable = dynamic(() => import("@/components/member/MemberTable").then(m => ({ default: m.MemberTable })), {
  loading: () => <LoadingSpinner />,
});
const MemberScatterPlot = dynamic(() => import("@/components/member/MemberScatterPlot").then(m => ({ default: m.MemberScatterPlot })), {
  loading: () => <LoadingSpinner />,
});

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
      roleCategory: searchParams.get("role_category") || "all",
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
      role_category: s.roleCategory === "all" ? undefined : s.roleCategory,
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
        role_category: newState.roleCategory,
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

      {/* クイックフィルタプリセット */}
      <div className="flex items-center gap-2 mb-4 flex-wrap">
        <span className="text-xs text-muted-foreground mr-1">クイック絞り込み:</span>
        <Button
          variant="outline"
          size="sm"
          className="h-7 text-xs"
          onClick={() => updateParams({ grade: "F", sort_by: "total", sort_order: "asc", page: undefined })}
        >
          低活動議員(F)
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="h-7 text-xs"
          onClick={() => updateParams({ grade: "A", sort_by: "total", sort_order: "desc", page: undefined })}
        >
          高活動議員(A)
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="h-7 text-xs"
          onClick={() => updateParams({ sort_by: "legislative_activity", sort_order: "desc", page: undefined, grade: undefined })}
        >
          立法活動順
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="h-7 text-xs"
          onClick={() => updateParams({ sort_by: "question_quality", sort_order: "desc", page: undefined, grade: undefined })}
        >
          質問品質順
        </Button>
      </div>

      <AdvancedMemberFilter state={filterState} onChange={handleFilterChange} />

      {/* アクティブフィルタサマリー */}
      {(() => {
        const tags: { label: string; clear: () => void }[] = [];
        if (filterState.search) tags.push({ label: `検索: ${filterState.search}`, clear: () => handleFilterChange({ ...filterState, search: "" }) });
        if (filterState.chamber !== "all") tags.push({ label: CHAMBER_LABELS[filterState.chamber] || filterState.chamber, clear: () => handleFilterChange({ ...filterState, chamber: "all" }) });
        if (filterState.party !== "all") tags.push({ label: filterState.party, clear: () => handleFilterChange({ ...filterState, party: "all" }) });
        if (filterState.district) tags.push({ label: `選挙区: ${filterState.district}`, clear: () => handleFilterChange({ ...filterState, district: "" }) });
        if (filterState.grades.length > 0) tags.push({ label: `グレード: ${filterState.grades.join(",")}`, clear: () => handleFilterChange({ ...filterState, grades: [] }) });
        if (isRangeActive(filterState.scoreRange)) tags.push({ label: `スコア: ${filterState.scoreRange[0]}-${filterState.scoreRange[1]}`, clear: () => handleFilterChange({ ...filterState, scoreRange: [0, 100] }) });
        const axisRanges: { key: keyof AdvancedFilterState; axis: string }[] = [
          { key: "laRange", axis: "legislative_activity" },
          { key: "vbRange", axis: "voting_behavior" },
          { key: "piRange", axis: "policy_influence" },
          { key: "trRange", axis: "transparency" },
          { key: "qqRange", axis: "question_quality" },
        ];
        for (const { key, axis } of axisRanges) {
          const range = filterState[key] as [number, number];
          if (isRangeActive(range)) tags.push({ label: `${AXIS_LABELS[axis]}: ${range[0]}-${range[1]}`, clear: () => handleFilterChange({ ...filterState, [key]: [0, 100] }) });
        }
        if (tags.length === 0) return null;
        return (
          <div className="flex flex-wrap gap-1.5 mb-3">
            {tags.map((tag) => (
              <Badge key={tag.label} variant="secondary" className="flex items-center gap-1 text-xs py-0.5">
                {tag.label}
                <button type="button" onClick={tag.clear} className="ml-0.5 hover:text-foreground" aria-label={`${tag.label}を解除`}>&times;</button>
              </Badge>
            ))}
            {tags.length > 1 && (
              <button
                type="button"
                className="text-xs text-muted-foreground hover:text-foreground"
                onClick={() => handleFilterChange({
                  search: "", chamber: "all", party: "all", roleCategory: "all", district: "", grades: [],
                  scoreRange: [0, 100], laRange: [0, 100], vbRange: [0, 100], piRange: [0, 100], trRange: [0, 100], qqRange: [0, 100],
                })}
              >
                全解除
              </button>
            )}
          </div>
        );
      })()}

      {!isScatterView && (
        <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <p className="text-sm text-muted-foreground">{total}名の議員</p>
            {(() => {
              const hasActiveFilter = filterState.search || filterState.chamber !== "all" || filterState.party !== "all"
                || filterState.roleCategory !== "all" || filterState.district || filterState.grades.length > 0
                || isRangeActive(filterState.scoreRange) || isRangeActive(filterState.laRange) || isRangeActive(filterState.vbRange)
                || isRangeActive(filterState.piRange) || isRangeActive(filterState.trRange) || isRangeActive(filterState.qqRange);
              if (!hasActiveFilter || total === 0) return null;
              return (
                <Badge variant="outline" className="text-xs text-muted-foreground">
                  フィルタ適用中
                </Badge>
              );
            })()}
          </div>
          {filterState.district && total > 0 && total <= 10 && (
            <p className="text-xs text-blue-600">
              「{filterState.district}」の議員 — スコアを比較して投票の参考にしましょう
            </p>
          )}
        </div>
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
          <MemberList members={members} onResetFilters={() => handleFilterChange({
            search: "", chamber: "all", party: "all", roleCategory: "all", district: "", grades: [],
            scoreRange: [0, 100], laRange: [0, 100], vbRange: [0, 100], piRange: [0, 100], trRange: [0, 100], qqRange: [0, 100],
          })} />
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
