"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { PartyTrendResponse } from "@/lib/types";
import { useIsDark } from "@/lib/hooks";

interface PartyTrendChartProps {
  trendData: PartyTrendResponse;
  topParties: string[];
  colors: { stroke: string; fill: string }[];
}

export function PartyTrendChart({ trendData, topParties, colors }: PartyTrendChartProps) {
  const dark = useIsDark();
  const gridColor = dark ? "#334155" : "#e2e8f0";
  const tickColor = dark ? "#94a3b8" : "#475569";
  const tooltipBg = dark ? "#1e293b" : "#ffffff";
  const tooltipBorder = dark ? "#334155" : "#e2e8f0";

  const chartData = trendData.sessions.map((session) => {
    const point: Record<string, string | number> = {
      session: `第${session.session_number}回`,
    };
    for (const party of topParties) {
      const p = session.parties[party];
      if (p) {
        point[party] = p.average_score;
      }
    }
    return point;
  });

  return (
    <ResponsiveContainer width="100%" height={350}>
      <LineChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
        <XAxis
          dataKey="session"
          tick={{ fontSize: 12, fill: tickColor }}
          tickLine={false}
        />
        <YAxis
          domain={[0, 100]}
          tick={{ fontSize: 12, fill: tickColor }}
          tickLine={false}
          width={40}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: tooltipBg,
            border: `1px solid ${tooltipBorder}`,
            borderRadius: "8px",
            fontSize: "13px",
            color: tickColor,
          }}
          formatter={(value: number | undefined) => [`${value ?? 0}点`, undefined]}
          labelFormatter={(label: unknown) => String(label ?? "")}
        />
        <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "8px" }} />
        {topParties.map((party, idx) => (
          <Line
            key={party}
            type="monotone"
            dataKey={party}
            name={party}
            stroke={colors[idx % colors.length].stroke}
            strokeWidth={2}
            dot={{ r: 3, fill: colors[idx % colors.length].fill }}
            activeDot={{ r: 5 }}
            connectNulls
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
