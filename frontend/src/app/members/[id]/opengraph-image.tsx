import { ImageResponse } from "next/og";
import { getMember } from "@/lib/api";

export const runtime = "edge";
export const alt = "議員スコア";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const GRADE_BG: Record<string, string> = {
  A: "#10b981",
  B: "#3b82f6",
  C: "#eab308",
  D: "#f97316",
  F: "#ef4444",
};

const CHAMBER_LABELS: Record<string, string> = {
  representatives: "衆議院",
  councillors: "参議院",
};

const AXIS_LABELS: Record<string, string> = {
  legislative_activity: "立法活動",
  voting_behavior: "投票行動",
  policy_influence: "政策影響力",
  transparency: "透明性",
};

export default async function OGImage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;

  let name = "議員";
  let party = "無所属";
  let chamber = "";
  let grade = "-";
  let total = 0;
  let gradeBg = "#9ca3af";
  let axes: { label: string; value: number }[] = [];

  try {
    const member = await getMember(Number(id));
    name = member.name;
    party = member.party ?? "無所属";
    chamber = CHAMBER_LABELS[member.chamber] ?? member.chamber;

    const latestScore = member.scores?.[0] ?? null;
    if (latestScore) {
      grade = latestScore.grade;
      total = latestScore.total;
      gradeBg = GRADE_BG[grade] ?? "#9ca3af";
      axes = [
        { label: AXIS_LABELS.legislative_activity, value: latestScore.legislative_activity },
        { label: AXIS_LABELS.voting_behavior, value: latestScore.voting_behavior },
        { label: AXIS_LABELS.policy_influence, value: latestScore.policy_influence },
        { label: AXIS_LABELS.transparency, value: latestScore.transparency },
      ];
    }
  } catch {
    // fallback to defaults
  }

  return new ImageResponse(
    (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          width: "100%",
          height: "100%",
          backgroundColor: "#f8fafc",
          fontFamily: "sans-serif",
        }}
      >
        {/* Header */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "32px 48px",
            backgroundColor: "#1e293b",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <span style={{ color: "#3b82f6", fontSize: "36px", fontWeight: 700 }}>
              GiinScore
            </span>
          </div>
          <span style={{ color: "#94a3b8", fontSize: "20px" }}>
            政治家活動スコアリング
          </span>
        </div>

        {/* Body */}
        <div
          style={{
            display: "flex",
            flex: 1,
            padding: "48px",
            gap: "48px",
            alignItems: "center",
          }}
        >
          {/* Left: Member info */}
          <div style={{ display: "flex", flexDirection: "column", flex: 1 }}>
            <div style={{ display: "flex", alignItems: "center", gap: "20px", marginBottom: "16px" }}>
              {/* Grade circle */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  width: "100px",
                  height: "100px",
                  borderRadius: "50%",
                  backgroundColor: gradeBg,
                  color: "#fff",
                  fontSize: "48px",
                  fontWeight: 700,
                }}
              >
                {grade}
              </div>
              <div style={{ display: "flex", flexDirection: "column" }}>
                <span style={{ fontSize: "48px", fontWeight: 700, color: "#1e293b" }}>
                  {name}
                </span>
                <div style={{ display: "flex", gap: "12px", marginTop: "4px" }}>
                  <span style={{ fontSize: "22px", color: "#64748b" }}>{party}</span>
                  <span style={{ fontSize: "22px", color: "#64748b" }}>{chamber}</span>
                </div>
              </div>
            </div>

            {/* Total score */}
            <div style={{ display: "flex", alignItems: "baseline", gap: "8px", marginTop: "16px" }}>
              <span style={{ fontSize: "72px", fontWeight: 700, color: "#1e293b" }}>
                {total.toFixed(1)}
              </span>
              <span style={{ fontSize: "28px", color: "#94a3b8" }}>/ 100</span>
            </div>
          </div>

          {/* Right: Axis breakdown */}
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "16px",
              width: "400px",
            }}
          >
            {axes.map((axis) => (
              <div key={axis.label} style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ fontSize: "20px", color: "#475569" }}>{axis.label}</span>
                  <span style={{ fontSize: "20px", fontWeight: 600, color: "#1e293b" }}>
                    {axis.value.toFixed(1)}
                  </span>
                </div>
                <div
                  style={{
                    display: "flex",
                    width: "100%",
                    height: "16px",
                    backgroundColor: "#e2e8f0",
                    borderRadius: "8px",
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      width: `${Math.min(axis.value, 100)}%`,
                      height: "100%",
                      backgroundColor: "#3b82f6",
                      borderRadius: "8px",
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    ),
    { ...size },
  );
}
