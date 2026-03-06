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
