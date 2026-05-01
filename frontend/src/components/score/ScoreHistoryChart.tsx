"use client";

import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceArea,
} from "recharts";
import type { ScoreDetail } from "@/lib/types";

interface ScoreHistoryChartProps {
  scores: ScoreDetail[];
}

const LINE_CONFIG = [
  { dataKey: "total", name: "総合", color: "#1e40af", strokeWidth: 3 },
  { dataKey: "legislative_activity", name: "立法活動", color: "#059669", strokeWidth: 1.5 },
  { dataKey: "voting_behavior", name: "投票行動", color: "#d97706", strokeWidth: 1.5 },
  { dataKey: "policy_influence", name: "政策影響力", color: "#7c3aed", strokeWidth: 1.5 },
  { dataKey: "transparency", name: "透明性", color: "#dc2626", strokeWidth: 1.5 },
  { dataKey: "question_quality", name: "質問品質", color: "#0891b2", strokeWidth: 1.5 },
] as const;

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

export function ScoreHistoryChart({ scores }: ScoreHistoryChartProps) {
  const isDark = useIsDark();
  const gridColor = isDark ? "#334155" : "#e2e8f0";
  const tickColor = isDark ? "#94a3b8" : "#475569";
  const tooltipBg = isDark ? "#1e293b" : "#ffffff";
  const tooltipBorder = isDark ? "#475569" : "#e2e8f0";

  // 会期番号の昇順でソート
  const sortedScores = [...scores].sort(
    (a, b) => (a.session_number ?? 0) - (b.session_number ?? 0)
  );

  const data = sortedScores.map((s) => ({
    session_number: s.session_number != null ? `第${s.session_number}回` : "-",
    total: Math.round(s.total * 10) / 10,
    legislative_activity: Math.round(s.legislative_activity * 10) / 10,
    voting_behavior: Math.round(s.voting_behavior * 10) / 10,
    policy_influence: Math.round(s.policy_influence * 10) / 10,
    transparency: Math.round(s.transparency * 10) / 10,
    question_quality: Math.round(s.question_quality * 10) / 10,
  }));

  return (
    <div role="img" aria-label={`スコア推移グラフ: ${data.length}会期分のデータ`}>
    <ResponsiveContainer width="100%" height={350}>
      <LineChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
        <ReferenceArea y1={80} y2={100} fill="#10b981" fillOpacity={0.06} />
        <ReferenceArea y1={60} y2={80} fill="#3b82f6" fillOpacity={0.06} />
        <ReferenceArea y1={40} y2={60} fill="#eab308" fillOpacity={0.06} />
        <ReferenceArea y1={20} y2={40} fill="#f97316" fillOpacity={0.06} />
        <ReferenceArea y1={0} y2={20} fill="#ef4444" fillOpacity={0.06} />
        <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
        <XAxis
          dataKey="session_number"
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
          formatter={(value: number | undefined, name: string | undefined) => [`${value ?? 0}点`, name ?? ""]}
        />
        <Legend
          wrapperStyle={{ fontSize: "12px", paddingTop: "8px" }}
        />
        {LINE_CONFIG.map((line) => (
          <Line
            key={line.dataKey}
            type="monotone"
            dataKey={line.dataKey}
            name={line.name}
            stroke={line.color}
            strokeWidth={line.strokeWidth}
            dot={{ r: 3, fill: line.color }}
            activeDot={{ r: 5 }}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
    </div>
  );
}
