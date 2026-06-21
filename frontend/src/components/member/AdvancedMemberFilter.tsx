"use client";

import { useState, useEffect, useRef } from "react";
import { SlidersHorizontal, X } from "lucide-react";
import useSWR from "swr";
import { swrFetcher, buildQuery } from "@/lib/api";
import type { MemberWithScore, PaginatedResponse } from "@/lib/types";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Slider } from "@/components/ui/slider";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { useParties, useRoleCategories } from "@/lib/hooks";
import { GRADE_COLORS, AXIS_LABELS } from "@/lib/types";

const ROLE_CATEGORY_LABELS: Record<string, string> = {
  cabinet: "閣僚",
  ruling_senior: "与党幹部",
  ruling_junior: "与党一般",
  opposition_leader: "野党幹部",
  opposition_junior: "野党一般",
  chair: "委員長",
  unknown: "不明",
};

const GRADES = ["A", "B", "C", "D", "F"] as const;

export interface AdvancedFilterState {
  search: string;
  chamber: string;
  party: string;
  roleCategory: string;
  district: string;
  grades: string[];
  scoreRange: [number, number];
  laRange: [number, number];
  vbRange: [number, number];
  piRange: [number, number];
  trRange: [number, number];
  qqRange: [number, number];
}

const DEFAULT_RANGE: [number, number] = [0, 100];

export const DEFAULT_FILTER_STATE: AdvancedFilterState = {
  search: "",
  chamber: "all",
  party: "all",
  roleCategory: "all",
  district: "",
  grades: [],
  scoreRange: DEFAULT_RANGE,
  laRange: DEFAULT_RANGE,
  vbRange: DEFAULT_RANGE,
  piRange: DEFAULT_RANGE,
  trRange: DEFAULT_RANGE,
  qqRange: DEFAULT_RANGE,
};

interface FilterPreset {
  label: string;
  state: Partial<AdvancedFilterState>;
}

const FILTER_PRESETS: FilterPreset[] = [
  { label: "高評価議員", state: { grades: ["A", "B"], scoreRange: [60, 100] } },
  { label: "質問力上位", state: { qqRange: [70, 100] } },
  { label: "立法活動活発", state: { laRange: [60, 100] } },
  { label: "低評価議員", state: { grades: ["D", "F"], scoreRange: [0, 40] } },
];

interface AdvancedMemberFilterProps {
  state: AdvancedFilterState;
  onChange: (state: AdvancedFilterState) => void;
}

export function isRangeActive(range: [number, number]): boolean {
  return range[0] > 0 || range[1] < 100;
}

export function countActiveFilters(state: AdvancedFilterState): number {
  let count = 0;
  if (state.grades.length > 0) count++;
  if (isRangeActive(state.scoreRange)) count++;
  if (isRangeActive(state.laRange)) count++;
  if (isRangeActive(state.vbRange)) count++;
  if (isRangeActive(state.piRange)) count++;
  if (isRangeActive(state.trRange)) count++;
  if (isRangeActive(state.qqRange)) count++;
  return count;
}

function RangeSlider({
  label,
  value,
  onChange,
}: {
  label: string;
  value: [number, number];
  onChange: (v: [number, number]) => void;
}) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium">{label}</span>
        <span className="text-muted-foreground tabular-nums">
          {value[0]} - {value[1]}
        </span>
      </div>
      <Slider
        min={0}
        max={100}
        step={5}
        value={value}
        onValueChange={(v) => onChange(v as [number, number])}
      />
    </div>
  );
}

function DebouncedInput({
  value: externalValue,
  onChange: onExternalChange,
  delay = 300,
  ...props
}: Omit<React.ComponentProps<typeof Input>, "onChange"> & {
  onChange: (value: string) => void;
  delay?: number;
}) {
  const [localValue, setLocalValue] = useState(externalValue);
  const timerRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  // 外部値が変わったらローカルも同期
  useEffect(() => {
    setLocalValue(externalValue);
  }, [externalValue]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const v = e.target.value;
    setLocalValue(v);
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => onExternalChange(v), delay);
  };

  useEffect(() => {
    return () => clearTimeout(timerRef.current);
  }, []);

  return <Input {...props} value={localValue} onChange={handleChange} />;
}

/** 議員名検索 with オートコンプリートサジェスト */
function MemberSearchInput({
  value,
  onChange,
  className,
}: {
  value: string;
  onChange: (value: string) => void;
  className?: string;
}) {
  const [localValue, setLocalValue] = useState(value);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  const [debouncedQuery, setDebouncedQuery] = useState(value);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setLocalValue(value);
  }, [value]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const v = e.target.value;
    setLocalValue(v);
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      setDebouncedQuery(v);
      onChange(v);
    }, 300);
    setShowSuggestions(v.length >= 1);
  };

  useEffect(() => () => clearTimeout(timerRef.current), []);

  // サジェスト用データ取得
  const { data: suggestions } = useSWR<PaginatedResponse<MemberWithScore>>(
    debouncedQuery.length >= 1 ? `/members${buildQuery({ search: debouncedQuery, per_page: 5 })}` : null,
    swrFetcher,
    { revalidateOnFocus: false, dedupingInterval: 1000 },
  );

  // 外側クリックで閉じる
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const items = suggestions?.items ?? [];

  return (
    <div ref={containerRef} className={`relative ${className ?? ""}`}>
      <Input
        placeholder="議員名で検索..."
        value={localValue}
        onChange={handleChange}
        onFocus={() => localValue.length >= 1 && setShowSuggestions(true)}
      />
      {showSuggestions && items.length > 0 && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-popover border border-border rounded-lg shadow-lg z-50 max-h-60 overflow-auto">
          {items.map((m) => (
            <button
              key={m.id}
              type="button"
              className="w-full px-3 py-2 text-left hover:bg-muted/50 flex items-center gap-2 text-sm"
              onClick={() => {
                setLocalValue(m.name);
                onChange(m.name);
                setShowSuggestions(false);
              }}
            >
              <span className="font-medium">{m.name}</span>
              <span className="text-xs text-muted-foreground">{m.party ?? "無所属"}</span>
              {m.latest_score && (
                <span className="ml-auto text-xs text-muted-foreground">{m.latest_score.grade} {m.latest_score.total.toFixed(1)}</span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

const FILTER_OPEN_KEY = "giin-score-filter-open";

export function AdvancedMemberFilter({ state, onChange }: AdvancedMemberFilterProps) {
  const [open, setOpen] = useState(() => {
    if (typeof window === "undefined") return false;
    return localStorage.getItem(FILTER_OPEN_KEY) === "1";
  });

  useEffect(() => {
    try { localStorage.setItem(FILTER_OPEN_KEY, open ? "1" : "0"); } catch { /* ignore */ }
  }, [open]);
  const chamberParam = state.chamber === "all" ? undefined : state.chamber;
  const { data: parties } = useParties(chamberParam);
  const { data: roleCategories } = useRoleCategories(chamberParam);

  const activeCount = countActiveFilters(state);

  const update = (patch: Partial<AdvancedFilterState>) => {
    onChange({ ...state, ...patch });
  };

  const applyPreset = (preset: FilterPreset) => {
    onChange({ ...DEFAULT_FILTER_STATE, ...preset.state });
  };

  const toggleGrade = (g: string) => {
    const next = state.grades.includes(g)
      ? state.grades.filter((x) => x !== g)
      : [...state.grades, g];
    update({ grades: next });
  };

  const resetAdvanced = () => {
    update({
      grades: [],
      scoreRange: DEFAULT_RANGE,
      laRange: DEFAULT_RANGE,
      vbRange: DEFAULT_RANGE,
      piRange: DEFAULT_RANGE,
      trRange: DEFAULT_RANGE,
      qqRange: DEFAULT_RANGE,
    });
  };

  return (
    <div className="space-y-3 mb-6 sticky top-14 z-30 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 -mx-4 px-4 py-3 border-b border-transparent has-[+*]:border-border">
      {/* 基本フィルタ行 */}
      <div className="flex flex-col sm:flex-row gap-3 flex-wrap items-start">
        <MemberSearchInput
          value={state.search}
          onChange={(v) => update({ search: v })}
          className="sm:max-w-xs"
        />
        <Select value={state.chamber} onValueChange={(v) => update({ chamber: v })}>
          <SelectTrigger className="sm:w-40">
            <SelectValue placeholder="院を選択" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全て</SelectItem>
            <SelectItem value="representatives">衆議院</SelectItem>
            <SelectItem value="councillors">参議院</SelectItem>
          </SelectContent>
        </Select>
        <Select value={state.party} onValueChange={(v) => update({ party: v })}>
          <SelectTrigger className="sm:w-48">
            <SelectValue placeholder="政党を選択" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全政党</SelectItem>
            {(parties ?? []).map((p) => (
              <SelectItem key={p} value={p}>{p}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={state.roleCategory} onValueChange={(v) => update({ roleCategory: v })}>
          <SelectTrigger className="sm:w-40" aria-label="役職を選択">
            <SelectValue placeholder="役職を選択" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全役職</SelectItem>
            {(roleCategories ?? []).map((c) => (
              <SelectItem key={c} value={c}>{ROLE_CATEGORY_LABELS[c] ?? c}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <DebouncedInput
          placeholder="選挙区で検索..."
          value={state.district}
          onChange={(v) => update({ district: v })}
          className="sm:max-w-[200px]"
        />
        <Button
          variant={open ? "default" : "outline"}
          size="sm"
          onClick={() => setOpen(!open)}
          className="gap-1.5"
        >
          <SlidersHorizontal className="size-4" />
          詳細フィルタ
          {activeCount > 0 && (
            <Badge variant="secondary" className="ml-1 px-1.5 py-0 text-xs">
              {activeCount}
            </Badge>
          )}
        </Button>
      </div>

      {/* プリセット */}
      <div className="flex gap-2 flex-wrap">
        <span className="text-xs text-muted-foreground leading-7">プリセット:</span>
        {FILTER_PRESETS.map((preset) => (
          <Button
            key={preset.label}
            variant="outline"
            size="sm"
            className="h-7 text-xs"
            onClick={() => applyPreset(preset)}
          >
            {preset.label}
          </Button>
        ))}
      </div>

      {/* 詳細フィルタパネル */}
      {open && (
        <Card>
          <CardContent className="pt-4 space-y-6">
            {/* グレード */}
            <div className="space-y-2">
              <span className="text-sm font-medium">グレード</span>
              <div className="flex gap-2 flex-wrap">
                {GRADES.map((g) => {
                  const checked = state.grades.includes(g);
                  return (
                    <label
                      key={g}
                      className="flex items-center gap-1.5 cursor-pointer"
                    >
                      <Checkbox
                        checked={checked}
                        onCheckedChange={() => toggleGrade(g)}
                      />
                      <span
                        className={`inline-flex items-center justify-center size-6 rounded text-xs font-bold text-white ${GRADE_COLORS[g]}`}
                      >
                        {g}
                      </span>
                    </label>
                  );
                })}
              </div>
            </div>

            {/* スコアレンジ */}
            <RangeSlider
              label="総合スコア"
              value={state.scoreRange}
              onChange={(v) => update({ scoreRange: v })}
            />

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              <RangeSlider
                label={AXIS_LABELS.legislative_activity}
                value={state.laRange}
                onChange={(v) => update({ laRange: v })}
              />
              <RangeSlider
                label={AXIS_LABELS.voting_behavior}
                value={state.vbRange}
                onChange={(v) => update({ vbRange: v })}
              />
              <RangeSlider
                label={AXIS_LABELS.policy_influence}
                value={state.piRange}
                onChange={(v) => update({ piRange: v })}
              />
              <RangeSlider
                label={AXIS_LABELS.transparency}
                value={state.trRange}
                onChange={(v) => update({ trRange: v })}
              />
              <RangeSlider
                label={AXIS_LABELS.question_quality}
                value={state.qqRange}
                onChange={(v) => update({ qqRange: v })}
              />
            </div>

            {activeCount > 0 && (
              <Button variant="ghost" size="sm" onClick={resetAdvanced} className="gap-1">
                <X className="size-3" />
                フィルタをリセット
              </Button>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
