"use client";

import { useEffect } from "react";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Page error:", error);
  }, [error]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-16 text-center">
      <h1 className="text-4xl font-bold text-muted-foreground/30 mb-4">Error</h1>
      <h2 className="text-xl font-semibold text-foreground mb-2">エラーが発生しました</h2>
      <p className="text-sm text-muted-foreground mb-8">
        ページの読み込み中に問題が発生しました。再度お試しください。
      </p>
      <button
        onClick={reset}
        className="inline-flex items-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
      >
        再読み込み
      </button>
    </div>
  );
}
