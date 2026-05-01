"use client";

import { useState, useEffect } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  LabelList,
} from "recharts";
import type { PartyStatsEntry } from "@/lib/types";

function useIsDark() {
  const [dark, setDark] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const check = () => setDark(document.documentElement.classList.contains("dark") || mq.matches);
    check();
    const obs = new MutationObserver(check);
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
    mq.addEventListener("change", check);
    return () => { obs.disconnect(); mq.removeEventListener("change", check); };
  }, []);
  return dark;
}

interface PartyBarChartProps {
  items: PartyStatsEntry[];
}

export function PartyBarChart({ items }: PartyBarChartProps) {
  const dark = useIsDark();
  const gridColor = dark ? "#334155" : "#e2e8f0";
  const tickColor = dark ? "#94a3b8" : "#475569";
  const tooltipBg = dark ? "#1e293b" : "#ffffff";
  const tooltipBorder = dark ? "#334155" : "#e2e8f0";

  if (items.length === 0) {
    return (
      <p className="text-center text-sm text-muted-foreground py-8">
        データがありません
      </p>
    );
  }

  const data = items.map((item) => ({
    name: item.party.length > 6 ? item.party.slice(0, 6) + "…" : item.party,
    fullName: item.party,
    member_count: item.member_count,
    平均スコア: item.average_score,
    立法活動: item.average_legislative_activity,
    投票行動: item.average_voting_behavior,
    政策影響力: item.average_policy_influence,
    透明性: item.average_transparency,
    質問品質: item.average_question_quality,
  }));

  return (
    <ResponsiveContainer width="100%" height={Math.max(300, items.length * 50)}>
      <BarChart data={data} layout="vertical" margin={{ left: 20, right: 40 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
        <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 12, fill: tickColor }} />
        <YAxis type="category" dataKey="name" width={80} tick={{ fontSize: 11, fill: tickColor }} />
        <Tooltip
          formatter={(value) => [(value as number).toFixed(1)]}
          labelFormatter={(_label, payload) => {
            if (payload && payload.length > 0) {
              const item = payload[0].payload as { fullName: string; member_count: number };
              return `${item.fullName} (${item.member_count}名)`;
            }
            return String(_label);
          }}
          contentStyle={{ backgroundColor: tooltipBg, borderColor: tooltipBorder }}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Bar dataKey="平均スコア" fill="#3b82f6" radius={[0, 4, 4, 0]}>
          <LabelList dataKey="平均スコア" position="right" formatter={(v) => Number(v).toFixed(1)} style={{ fontSize: 11, fill: tickColor }} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
