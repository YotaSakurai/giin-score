import Link from "next/link";

export default function RootNotFound() {
  return (
    <html lang="ja">
      <body style={{ fontFamily: "sans-serif" }}>
        <div style={{ maxWidth: "600px", margin: "80px auto", textAlign: "center" }}>
          <h1 style={{ fontSize: "4rem", color: "#ccc", marginBottom: "16px" }}>404</h1>
          <h2 style={{ fontSize: "1.2rem", marginBottom: "8px" }}>ページが見つかりません</h2>
          <p style={{ color: "#666", marginBottom: "24px" }}>
            お探しのページは存在しないか、移動された可能性があります。
          </p>
          <Link
            href="/"
            style={{
              padding: "8px 16px",
              borderRadius: "6px",
              background: "#0070f3",
              color: "white",
              textDecoration: "none",
            }}
          >
            トップページへ
          </Link>
        </div>
      </body>
    </html>
  );
}
