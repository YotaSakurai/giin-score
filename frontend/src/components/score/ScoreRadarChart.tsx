"use client";

import { PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart, ResponsiveContainer } from "recharts";

interface ScoreRadarChartProps {
  legislative_activity: number;
  voting_behavior: number;
  policy_influence: number;
  transparency: number;
}

export function ScoreRadarChart({ legislative_activity, voting_behavior, policy_influence, transparency }: ScoreRadarChartProps) {
  const data = [
    { axis: "立法活動", value: legislative_activity },
    { axis: "投票行動", value: voting_behavior },
    { axis: "政策影響力", value: policy_influence },
    { axis: "透明性", value: transparency },
  ];

  return (
    <ResponsiveContainer width="100%" height={280}>
      <RadarChart data={data} cx="50%" cy="50%" outerRadius="70%">
        <PolarGrid stroke="#e2e8f0" />
        <PolarAngleAxis dataKey="axis" tick={{ fontSize: 12, fill: "#475569" }} />
        <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fontSize: 10 }} />
        <Radar name="スコア" dataKey="value" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.25} strokeWidth={2} />
      </RadarChart>
    </ResponsiveContainer>
  );
}
