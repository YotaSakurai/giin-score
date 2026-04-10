"use client";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="ja">
      <body>
        <div style={{ maxWidth: "600px", margin: "80px auto", textAlign: "center", fontFamily: "sans-serif" }}>
          <h1 style={{ fontSize: "2rem", color: "#888", marginBottom: "16px" }}>Error</h1>
          <h2 style={{ fontSize: "1.2rem", marginBottom: "8px" }}>エラーが発生しました</h2>
          <p style={{ color: "#666", marginBottom: "24px" }}>
            {error.message || "予期しないエラーが発生しました。再度お試しください。"}
          </p>
          <button
            onClick={reset}
            style={{
              padding: "8px 16px",
              borderRadius: "6px",
              border: "none",
              background: "#0070f3",
              color: "white",
              cursor: "pointer",
            }}
          >
            再読み込み
          </button>
        </div>
      </body>
    </html>
  );
}
