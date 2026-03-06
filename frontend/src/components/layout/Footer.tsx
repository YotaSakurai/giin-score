export function Footer() {
  return (
    <footer className="border-t bg-muted/50 mt-auto">
      <div className="mx-auto max-w-7xl px-4 py-6">
        <p className="text-xs text-muted-foreground text-center leading-relaxed">
          本スコアは国会の公開データに基づく活動量の可視化であり、政治家の能力・人格・政策の正しさを評価するものではありません。
        </p>
        <p className="text-xs text-muted-foreground/70 text-center mt-2">
          &copy; 2026 GiinScore - データソース: 国会会議録API, 衆議院, 参議院, SmartNews SMRI
        </p>
      </div>
    </footer>
  );
}
