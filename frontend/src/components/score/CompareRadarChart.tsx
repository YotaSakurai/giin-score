"use client";

import { useState, useEffect } from "react";
import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
} from "recharts";

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

interface MemberScore {
  name: string;
  legislative_activity: number;
  voting_behavior: number;
  policy_influence: number;
  transparency: number;
  question_quality: number;
  color: { stroke: string; fill: string };
}

interface CompareRadarChartProps {
  members: MemberScore[];
}

export function CompareRadarChart({ members }: CompareRadarChartProps) {
  const dark = useIsDark();
  const gridColor = dark ? "#334155" : "#e2e8f0";
  const tickColor = dark ? "#94a3b8" : "#475569";

  const axes = [
    { key: "legislative_activity", label: "立法活動" },
    { key: "voting_behavior", label: "投票行動" },
    { key: "policy_influence", label: "政策影響力" },
    { key: "transparency", label: "透明性" },
    { key: "question_quality", label: "質問品質" },
  ] as const;

  // Rechartsに渡すdata形式: 各軸をrowにし、各議員の値をkeyとして持つ
  const data = axes.map((axis) => {
    const row: Record<string, string | number> = { axis: axis.label };
    members.forEach((m, idx) => {
      row[`member_${idx}`] = m[axis.key];
    });
    return row;
  });

  const ariaLabel = `レーダーチャート: ${members.map((m) => m.name).join("、")}の5軸スコア比較`;

  return (
    <div role="img" aria-label={ariaLabel}>
      <ResponsiveContainer width="100%" height={320}>
        <RadarChart data={data} cx="50%" cy="50%" outerRadius="70%">
          <PolarGrid stroke={gridColor} />
          <PolarAngleAxis
            dataKey="axis"
            tick={{ fontSize: 12, fill: tickColor }}
          />
          <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fontSize: 10 }} />
          {members.map((m, idx) => (
            <Radar
              key={m.name}
              name={m.name}
              dataKey={`member_${idx}`}
              stroke={m.color.stroke}
              fill={m.color.fill}
              fillOpacity={0.12}
              strokeWidth={2}
            />
          ))}
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
