"use client";

import { useMemo } from "react";
import { useRouter } from "next/navigation";
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  LabelList,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { MemberScorePoint } from "@/lib/types";
import { SCORE_AXIS_OPTIONS, CHAMBER_LABELS } from "@/lib/types";

type ColorBy = "party" | "grade" | "chamber";

interface MemberScatterPlotProps {
  data: MemberScorePoint[];
  xAxis: string;
  yAxis: string;
  colorBy: ColorBy;
  onXAxisChange: (v: string) => void;
  onYAxisChange: (v: string) => void;
  onColorByChange: (v: ColorBy) => void;
}

const GRADE_HEX: Record<string, string> = {
  A: "#10b981",
  B: "#3b82f6",
  C: "#eab308",
  D: "#f97316",
  F: "#ef4444",
};

const CHAMBER_HEX: Record<string, string> = {
  representatives: "#6366f1",
  councillors: "#ec4899",
};

// 政党ごとの色パレット
const PARTY_COLORS = [
  "#3b82f6", "#ef4444", "#10b981", "#f59e0b", "#8b5cf6",
  "#ec4899", "#06b6d4", "#84cc16", "#f97316", "#6366f1",
  "#14b8a6", "#e11d48", "#a855f7", "#0ea5e9", "#22c55e",
];

function getAxisLabel(key: string): string {
  return SCORE_AXIS_OPTIONS.find((o) => o.value === key)?.label ?? key;
}

function getVal(point: MemberScorePoint, axis: string): number {
  return point[axis as keyof MemberScorePoint] as number ?? 0;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{ payload: MemberScorePoint }>;
  xAxis: string;
  yAxis: string;
}

function CustomTooltip({ active, payload, xAxis, yAxis }: CustomTooltipProps) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="rounded-md border bg-background p-2 shadow-md text-sm">
      <p className="font-medium">{d.name}</p>
      <p className="text-muted-foreground">{d.party || "無所属"}</p>
      <p>{getAxisLabel(xAxis)}: {getVal(d, xAxis).toFixed(1)}</p>
      <p>{getAxisLabel(yAxis)}: {getVal(d, yAxis).toFixed(1)}</p>
    </div>
  );
}

const OUTLIER_COUNT = 5;

export function MemberScatterPlot({
  data,
  xAxis,
  yAxis,
  colorBy,
  onXAxisChange,
  onYAxisChange,
  onColorByChange,
}: MemberScatterPlotProps) {
  const router = useRouter();

  // 回帰直線の傾き・切片（最小二乗法）
  const regression = useMemo(() => {
    if (data.length < 2) return null;
    let sumX = 0, sumY = 0, sumXY = 0, sumXX = 0;
    const n = data.length;
    for (const d of data) {
      const x = getVal(d, xAxis);
      const y = getVal(d, yAxis);
      sumX += x;
      sumY += y;
      sumXY += x * y;
      sumXX += x * x;
    }
    const denom = n * sumXX - sumX * sumX;
    if (Math.abs(denom) < 1e-10) return null;
    const slope = (n * sumXY - sumX * sumY) / denom;
    const intercept = (sumY - slope * sumX) / n;
    // R²
    const meanY = sumY / n;
    let ssTot = 0, ssRes = 0;
    for (const d of data) {
      const x = getVal(d, xAxis);
      const y = getVal(d, yAxis);
      const predicted = slope * x + intercept;
      ssTot += (y - meanY) ** 2;
      ssRes += (y - predicted) ** 2;
    }
    const r2 = ssTot > 0 ? 1 - ssRes / ssTot : 0;
    return { slope, intercept, r2 };
  }, [data, xAxis, yAxis]);

  // 外れ値（X+Yの上位N点）のID集合
  const outlierIds = useMemo(() => {
    if (data.length <= OUTLIER_COUNT) return new Set(data.map((d) => d.id));
    const scored = data.map((d) => ({
      id: d.id,
      combined: getVal(d, xAxis) + getVal(d, yAxis),
    }));
    scored.sort((a, b) => b.combined - a.combined);
    return new Set(scored.slice(0, OUTLIER_COUNT).map((s) => s.id));
  }, [data, xAxis, yAxis]);

  // グループ化
  const groups = groupData(data, colorBy);

  function groupData(
    points: MemberScorePoint[],
    by: ColorBy
  ): { name: string; color: string; data: MemberScorePoint[] }[] {
    const map = new Map<string, MemberScorePoint[]>();
    for (const p of points) {
      let key: string;
      if (by === "grade") key = p.grade;
      else if (by === "chamber") key = p.chamber;
      else key = p.party || "無所属";
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(p);
    }

    const entries = Array.from(map.entries()).sort((a, b) => a[0].localeCompare(b[0]));
    return entries.map(([name, pts], i) => ({
      name: by === "chamber" ? (CHAMBER_LABELS[name] || name) : name,
      color:
        by === "grade"
          ? (GRADE_HEX[name] || "#94a3b8")
          : by === "chamber"
            ? (CHAMBER_HEX[name] || "#94a3b8")
            : PARTY_COLORS[i % PARTY_COLORS.length],
      data: pts,
    }));
  }

  return (
    <div className="space-y-4">
      {/* セレクター */}
      <div className="flex flex-wrap gap-3 items-center">
        <div className="flex items-center gap-1.5">
          <span className="text-sm text-muted-foreground">X軸:</span>
          <Select value={xAxis} onValueChange={onXAxisChange}>
            <SelectTrigger className="w-36">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {SCORE_AXIS_OPTIONS.map((o) => (
                <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-sm text-muted-foreground">Y軸:</span>
          <Select value={yAxis} onValueChange={onYAxisChange}>
            <SelectTrigger className="w-36">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {SCORE_AXIS_OPTIONS.map((o) => (
                <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-sm text-muted-foreground">色分け:</span>
          <Select value={colorBy} onValueChange={(v) => onColorByChange(v as ColorBy)}>
            <SelectTrigger className="w-28">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="party">政党</SelectItem>
              <SelectItem value="grade">グレード</SelectItem>
              <SelectItem value="chamber">院</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* チャート */}
      {data.length === 0 ? (
        <div className="flex items-center justify-center h-[500px] text-muted-foreground border rounded-md">
          該当する議員が見つかりません。フィルタ条件を変更してください。
        </div>
      ) : (
      <div role="img" aria-label={`散布図: X軸=${SCORE_AXIS_OPTIONS.find(o => o.value === xAxis)?.label ?? xAxis}, Y軸=${SCORE_AXIS_OPTIONS.find(o => o.value === yAxis)?.label ?? yAxis}`}>
      <ResponsiveContainer width="100%" height={500}>
        <ScatterChart margin={{ top: 10, right: 20, bottom: 20, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            type="number"
            dataKey={(d: MemberScorePoint) => getVal(d, xAxis)}
            name={getAxisLabel(xAxis)}
            domain={[0, 100]}
            label={{ value: getAxisLabel(xAxis), position: "bottom", offset: 0 }}
          />
          <YAxis
            type="number"
            dataKey={(d: MemberScorePoint) => getVal(d, yAxis)}
            name={getAxisLabel(yAxis)}
            domain={[0, 100]}
            label={{ value: getAxisLabel(yAxis), angle: -90, position: "insideLeft" }}
          />
          <Tooltip content={<CustomTooltip xAxis={xAxis} yAxis={yAxis} />} />
          <Legend />
          {regression && (
            <ReferenceLine
              segment={[
                { x: 0, y: Math.max(0, Math.min(100, regression.intercept)) },
                { x: 100, y: Math.max(0, Math.min(100, regression.slope * 100 + regression.intercept)) },
              ]}
              stroke="#94a3b8"
              strokeWidth={1.5}
              strokeDasharray="6 3"
              opacity={0.7}
              label={{ value: `R²=${regression.r2.toFixed(2)}`, position: "insideTopRight", fontSize: 10, fill: "#94a3b8" }}
              ifOverflow="extendDomain"
            />
          )}
          {groups.map((group) => (
            <Scatter
              key={group.name}
              name={group.name}
              data={group.data}
              fill={group.color}
              onClick={(d: { payload?: MemberScorePoint }) => {
                if (d?.payload?.id) router.push(`/members/${d.payload.id}`);
              }}
              cursor="pointer"
            >
              <LabelList
                dataKey="name"
                position="top"
                offset={8}
                style={{ fontSize: 10, fill: "#6b7280" }}
                content={({ x, y, value, index }) => {
                  const point = group.data[index as number];
                  if (!point || !outlierIds.has(point.id)) return null;
                  return (
                    <text x={x as number} y={(y as number) - 8} textAnchor="middle" fontSize={10} fill="#6b7280">
                      {value}
                    </text>
                  );
                }}
              />
            </Scatter>
          ))}
        </ScatterChart>
      </ResponsiveContainer>
      </div>
      )}
    </div>
  );
}
