"use client";

import { PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart, ResponsiveContainer } from "recharts";

interface ScoreRadarChartProps {
  legislative_activity: number;
  voting_behavior: number;
  policy_influence: number;
  transparency: number;
  question_quality: number;
}

export function ScoreRadarChart({ legislative_activity, voting_behavior, policy_influence, transparency, question_quality }: ScoreRadarChartProps) {
  const data = [
    { axis: "立法活動", value: legislative_activity },
    { axis: "投票行動", value: voting_behavior },
    { axis: "政策影響力", value: policy_influence },
    { axis: "透明性", value: transparency },
    { axis: "質問品質", value: question_quality },
  ];

  const ariaLabel = `5軸レーダーチャート: 立法活動${legislative_activity.toFixed(0)}, 投票行動${voting_behavior.toFixed(0)}, 政策影響力${policy_influence.toFixed(0)}, 透明性${transparency.toFixed(0)}, 質問品質${question_quality.toFixed(0)}`;

  return (
    <div role="img" aria-label={ariaLabel}>
      <ResponsiveContainer width="100%" height={280}>
        <RadarChart data={data} cx="50%" cy="50%" outerRadius="70%">
          <PolarGrid stroke="#e2e8f0" />
          <PolarAngleAxis dataKey="axis" tick={{ fontSize: 12, fill: "#475569" }} />
          <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fontSize: 10 }} />
          <Radar name="スコア" dataKey="value" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.25} strokeWidth={2} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
