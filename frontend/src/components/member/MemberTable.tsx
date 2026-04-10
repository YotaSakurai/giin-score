"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { ArrowUpDown, ArrowUp, ArrowDown, Download } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { MemberWithScore } from "@/lib/types";
import { CHAMBER_LABELS, GRADE_COLORS, AXIS_LABELS } from "@/lib/types";

interface MemberTableProps {
  members: MemberWithScore[];
  sortBy: string;
  sortOrder: "asc" | "desc";
  onSortChange: (sortBy: string, sortOrder: "asc" | "desc") => void;
}

interface ColumnDef {
  key: string;
  label: string;
  sortable: boolean;
  defaultVisible: boolean;
}

const COLUMNS: ColumnDef[] = [
  { key: "name", label: "議員名", sortable: true, defaultVisible: true },
  { key: "party", label: "政党", sortable: false, defaultVisible: true },
  { key: "chamber", label: "院", sortable: false, defaultVisible: true },
  { key: "district", label: "選挙区", sortable: false, defaultVisible: false },
  { key: "total", label: "総合", sortable: true, defaultVisible: true },
  { key: "grade", label: "グレード", sortable: false, defaultVisible: true },
  { key: "legislative_activity", label: AXIS_LABELS.legislative_activity, sortable: true, defaultVisible: true },
  { key: "voting_behavior", label: AXIS_LABELS.voting_behavior, sortable: true, defaultVisible: true },
  { key: "policy_influence", label: AXIS_LABELS.policy_influence, sortable: true, defaultVisible: false },
  { key: "transparency", label: AXIS_LABELS.transparency, sortable: true, defaultVisible: false },
  { key: "question_quality", label: AXIS_LABELS.question_quality, sortable: true, defaultVisible: true },
];

const STORAGE_KEY = "member-table-columns";

function getInitialColumns(): string[] {
  if (typeof window === "undefined") return COLUMNS.filter((c) => c.defaultVisible).map((c) => c.key);
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) return JSON.parse(saved);
  } catch { /* ignore */ }
  return COLUMNS.filter((c) => c.defaultVisible).map((c) => c.key);
}

function SortIcon({ columnKey, sortBy, sortOrder }: { columnKey: string; sortBy: string; sortOrder: string }) {
  if (sortBy !== columnKey) return <ArrowUpDown className="size-3 ml-1 opacity-40" />;
  return sortOrder === "asc"
    ? <ArrowUp className="size-3 ml-1" />
    : <ArrowDown className="size-3 ml-1" />;
}

function getScoreValue(member: MemberWithScore, key: string): string {
  const score = member.latest_score;
  if (!score) return "-";
  const val = score[key as keyof typeof score];
  if (val === undefined || val === null) return "-";
  if (typeof val === "number") return val.toFixed(1);
  return String(val);
}

export function MemberTable({ members, sortBy, sortOrder, onSortChange }: MemberTableProps) {
  const router = useRouter();
  const [visibleCols, setVisibleCols] = useState<string[]>(getInitialColumns);
  const [selected, setSelected] = useState<Set<number>>(new Set());

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(visibleCols));
    } catch { /* ignore */ }
  }, [visibleCols]);

  const toggleColumn = (key: string) => {
    setVisibleCols((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]
    );
  };

  const toggleSelect = useCallback((id: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const toggleAll = useCallback(() => {
    setSelected((prev) =>
      prev.size === members.length
        ? new Set()
        : new Set(members.map((m) => m.id))
    );
  }, [members]);

  const handleSort = (key: string) => {
    if (sortBy === key) {
      onSortChange(key, sortOrder === "asc" ? "desc" : "asc");
    } else {
      onSortChange(key, "desc");
    }
  };

  const handleCompare = () => {
    const ids = Array.from(selected).join(",");
    router.push(`/compare?ids=${ids}`);
  };

  const handleCsvExport = useCallback(() => {
    const cols = COLUMNS.filter((c) => visibleCols.includes(c.key));
    const header = cols.map((c) => c.label).join(",");
    const rows = members.map((m) => {
      return cols.map((col) => {
        let val: string;
        if (col.key === "name") val = m.name;
        else if (col.key === "party") val = m.party || "";
        else if (col.key === "chamber") val = CHAMBER_LABELS[m.chamber] || m.chamber;
        else if (col.key === "district") val = m.district || "";
        else if (col.key === "grade") val = m.latest_score?.grade || "";
        else val = getScoreValue(m, col.key);
        // CSV安全化: カンマ・引用符を含む場合は引用符で囲む
        if (val.includes(",") || val.includes('"') || val.includes("\n")) {
          val = `"${val.replace(/"/g, '""')}"`;
        }
        return val;
      }).join(",");
    });
    const bom = "\uFEFF";
    const csv = bom + [header, ...rows].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `giin-score-members.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }, [members, visibleCols]);

  const cols = COLUMNS.filter((c) => visibleCols.includes(c.key));

  return (
    <div className="space-y-3">
      {/* カラムトグル + CSV */}
      <div className="flex flex-wrap gap-2 items-center">
        <span className="text-xs text-muted-foreground mr-1">表示列:</span>
        {COLUMNS.map((col) => (
          <label key={col.key} className="flex items-center gap-1 text-xs cursor-pointer">
            <Checkbox
              checked={visibleCols.includes(col.key)}
              onCheckedChange={() => toggleColumn(col.key)}
            />
            {col.label}
          </label>
        ))}
        <Button variant="outline" size="sm" onClick={handleCsvExport} className="ml-auto gap-1">
          <Download className="size-3.5" />
          CSV
        </Button>
      </div>

      {/* 選択アクション */}
      {selected.size > 0 && (
        <div className="flex items-center gap-3">
          <span className="text-sm text-muted-foreground">{selected.size}名を選択中</span>
          <Button size="sm" onClick={handleCompare} disabled={selected.size < 2}>
            比較する
          </Button>
          <Button size="sm" variant="ghost" onClick={() => setSelected(new Set())}>
            選択解除
          </Button>
        </div>
      )}

      {/* テーブル */}
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-10">
              <Checkbox
                checked={members.length > 0 && selected.size === members.length}
                onCheckedChange={toggleAll}
                aria-label="全て選択"
              />
            </TableHead>
            {cols.map((col) => (
              <TableHead key={col.key}>
                {col.sortable ? (
                  <button
                    className="inline-flex items-center hover:text-foreground transition-colors"
                    onClick={() => handleSort(col.key)}
                    aria-label={`${col.label}でソート`}
                  >
                    {col.label}
                    <span aria-hidden="true"><SortIcon columnKey={col.key} sortBy={sortBy} sortOrder={sortOrder} /></span>
                  </button>
                ) : (
                  col.label
                )}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {members.length === 0 ? (
            <TableRow>
              <TableCell colSpan={cols.length + 1} className="text-center py-8 text-muted-foreground">
                該当する議員が見つかりません
              </TableCell>
            </TableRow>
          ) : (
            members.map((member) => (
              <TableRow
                key={member.id}
                data-state={selected.has(member.id) ? "selected" : undefined}
                className="cursor-pointer"
                onClick={() => router.push(`/members/${member.id}`)}
              >
                <TableCell onClick={(e) => e.stopPropagation()}>
                  <Checkbox
                    checked={selected.has(member.id)}
                    onCheckedChange={() => toggleSelect(member.id)}
                    aria-label={`${member.name}を選択`}
                  />
                </TableCell>
                {cols.map((col) => (
                  <TableCell key={col.key}>
                    {col.key === "name" ? (
                      <span className="font-medium">{member.name}</span>
                    ) : col.key === "party" ? (
                      member.party || "-"
                    ) : col.key === "chamber" ? (
                      CHAMBER_LABELS[member.chamber] || member.chamber
                    ) : col.key === "district" ? (
                      member.district || "-"
                    ) : col.key === "grade" ? (
                      member.latest_score ? (
                        <Badge className={`${GRADE_COLORS[member.latest_score.grade]} text-white text-xs`}>
                          {member.latest_score.grade}
                        </Badge>
                      ) : (
                        "-"
                      )
                    ) : (
                      getScoreValue(member, col.key)
                    )}
                  </TableCell>
                ))}
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </div>
  );
}
