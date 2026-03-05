import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "GiinScore - 政治家活動スコアリングダッシュボード";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OGImage() {
  return new ImageResponse(
    (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          width: "100%",
          height: "100%",
          backgroundColor: "#1e293b",
          fontFamily: "sans-serif",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "24px",
          }}
        >
          <span style={{ fontSize: "72px", fontWeight: 700, color: "#3b82f6" }}>
            GiinScore
          </span>
          <span style={{ fontSize: "32px", color: "#e2e8f0" }}>
            政治家活動スコアリングダッシュボード
          </span>
          <div style={{ display: "flex", gap: "32px", marginTop: "32px" }}>
            {[
              { label: "立法活動", pct: "30%", color: "#3b82f6" },
              { label: "投票行動", pct: "25%", color: "#10b981" },
              { label: "政策影響力", pct: "25%", color: "#f59e0b" },
              { label: "透明性", pct: "20%", color: "#8b5cf6" },
            ].map((item) => (
              <div
                key={item.label}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: "8px",
                  padding: "24px",
                  backgroundColor: "#334155",
                  borderRadius: "16px",
                  width: "200px",
                }}
              >
                <div
                  style={{
                    width: "48px",
                    height: "48px",
                    borderRadius: "50%",
                    backgroundColor: item.color,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <span style={{ color: "#fff", fontSize: "16px", fontWeight: 700 }}>
                    {item.pct}
                  </span>
                </div>
                <span style={{ color: "#e2e8f0", fontSize: "18px" }}>{item.label}</span>
              </div>
            ))}
          </div>
          <span style={{ fontSize: "20px", color: "#94a3b8", marginTop: "24px" }}>
            国会の公開データに基づく議員の活動量を可視化
          </span>
        </div>
      </div>
    ),
    { ...size },
  );
}
