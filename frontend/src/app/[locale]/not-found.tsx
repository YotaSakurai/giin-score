import Link from "next/link";

export default function NotFound() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-16 text-center">
      <h1 className="text-6xl font-bold text-muted-foreground/30 mb-4">404</h1>
      <h2 className="text-xl font-semibold text-foreground mb-2">ページが見つかりません</h2>
      <p className="text-sm text-muted-foreground mb-8">
        お探しのページは存在しないか、移動された可能性があります。
      </p>
      <div className="flex justify-center gap-4">
        <Link
          href="/"
          className="inline-flex items-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          トップページへ
        </Link>
        <Link
          href="/members"
          className="inline-flex items-center rounded-md border border-input bg-background px-4 py-2 text-sm font-medium hover:bg-accent"
        >
          議員一覧へ
        </Link>
      </div>
    </div>
  );
}
