"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import type { PartyStatsEntry } from "@/lib/types";

interface PartyBarChartProps {
  items: PartyStatsEntry[];
}

export function PartyBarChart({ items }: PartyBarChartProps) {
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
    平均スコア: item.average_score,
    立法活動: item.average_legislative_activity,
    投票行動: item.average_voting_behavior,
    政策影響力: item.average_policy_influence,
    透明性: item.average_transparency,
    質問品質: item.average_question_quality,
  }));

  return (
    <ResponsiveContainer width="100%" height={Math.max(300, items.length * 50)}>
      <BarChart data={data} layout="vertical" margin={{ left: 20, right: 20 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 12 }} />
        <YAxis type="category" dataKey="name" width={80} tick={{ fontSize: 11 }} />
        <Tooltip
          formatter={(value) => [(value as number).toFixed(1)]}
          labelFormatter={(_label, payload) => {
            if (payload && payload.length > 0) {
              const item = payload[0].payload as { fullName: string };
              return item.fullName;
            }
            return String(_label);
          }}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Bar dataKey="平均スコア" fill="#3b82f6" radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
