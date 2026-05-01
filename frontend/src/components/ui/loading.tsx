export function LoadingSpinner({ className = "" }: { className?: string }) {
  return (
    <div role="status" aria-label="読み込み中" className={`flex items-center justify-center py-12 ${className}`}>
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-muted border-t-primary" />
      <span className="sr-only">読み込み中</span>
    </div>
  );
}

export function LoadingSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div role="status" aria-label="読み込み中" className="space-y-3">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="animate-pulse">
          <div className="h-16 rounded-lg bg-muted" />
        </div>
      ))}
      <span className="sr-only">読み込み中</span>
    </div>
  );
}

/** テーブル形式のスケルトン（発言・投票タブ用） */
export function TableSkeleton({ rows = 5, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div role="status" aria-label="読み込み中" className="space-y-2">
      <div className="flex gap-4 border-b pb-2">
        {Array.from({ length: cols }).map((_, i) => (
          <div key={i} className="animate-pulse h-4 rounded bg-muted flex-1" />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex gap-4 py-2">
          {Array.from({ length: cols }).map((_, j) => (
            <div key={j} className="animate-pulse h-5 rounded bg-muted flex-1" style={{ animationDelay: `${(i * cols + j) * 50}ms` }} />
          ))}
        </div>
      ))}
      <span className="sr-only">読み込み中</span>
    </div>
  );
}

/** カード形式のスケルトン（質問品質・質問主意書タブ用） */
export function CardSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div role="status" aria-label="読み込み中" className="space-y-3">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="animate-pulse border-l-4 border-l-muted rounded-r-lg border p-3 space-y-2" style={{ animationDelay: `${i * 100}ms` }}>
          <div className="flex justify-between">
            <div className="h-4 w-2/3 rounded bg-muted" />
            <div className="h-6 w-10 rounded bg-muted" />
          </div>
          <div className="h-3 w-1/3 rounded bg-muted" />
          <div className="grid grid-cols-4 gap-2">
            {Array.from({ length: 4 }).map((_, j) => (
              <div key={j} className="h-2 rounded-full bg-muted" />
            ))}
          </div>
        </div>
      ))}
      <span className="sr-only">読み込み中</span>
    </div>
  );
}
