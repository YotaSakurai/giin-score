"use client";

import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { useLastUpdated } from "@/lib/hooks";

export function Footer() {
  const t = useTranslations("footer");
  const { data } = useLastUpdated();

  const lastUpdated = data?.last_updated
    ? new Date(data.last_updated).toLocaleDateString("ja-JP", {
        year: "numeric",
        month: "long",
        day: "numeric",
      })
    : null;

  return (
    <footer className="border-t bg-muted/50 mt-auto">
      <div className="mx-auto max-w-7xl px-4 py-6">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 mb-6">
          <div>
            <p className="text-sm font-semibold text-foreground mb-2">GiinScore</p>
            <p className="text-xs text-muted-foreground leading-relaxed">
              {t("description")}
            </p>
          </div>
          <div>
            <p className="text-xs font-semibold text-foreground mb-2">ページ</p>
            <div className="flex flex-col gap-1">
              <Link href="/" className="text-xs text-muted-foreground hover:text-primary">ランキング</Link>
              <Link href="/members" className="text-xs text-muted-foreground hover:text-primary">議員一覧</Link>
              <Link href="/parties" className="text-xs text-muted-foreground hover:text-primary">政党別統計</Link>
              <Link href="/quality-ranking" className="text-xs text-muted-foreground hover:text-primary">質問品質ランキング</Link>
              <Link href="/bills" className="text-xs text-muted-foreground hover:text-primary">法案一覧</Link>
              <Link href="/compare" className="text-xs text-muted-foreground hover:text-primary">議員比較</Link>
              <Link href="/favorites" className="text-xs text-muted-foreground hover:text-primary">お気に入り</Link>
              <Link href="/about" className="text-xs text-muted-foreground hover:text-primary">スコアについて</Link>
              <Link href="/api-docs" className="text-xs text-muted-foreground hover:text-primary">API</Link>
            </div>
          </div>
          <div>
            <p className="text-xs font-semibold text-foreground mb-2">{t("dataSource")}</p>
            <div className="flex flex-col gap-1">
              <a href="https://kokkai.ndl.go.jp" target="_blank" rel="noopener noreferrer" className="text-xs text-muted-foreground hover:text-primary">
                {t("kokkai")}
              </a>
              <Link href="/data-quality" className="text-xs text-muted-foreground hover:text-primary">データ品質</Link>
            </div>
            {lastUpdated && (
              <p className="text-xs text-muted-foreground/70 mt-2">
                最終更新: {lastUpdated}
              </p>
            )}
          </div>
        </div>
        <div className="border-t pt-4">
          <p className="text-xs text-muted-foreground text-center leading-relaxed">
            {t("disclaimer")}
          </p>
          <p className="text-xs text-muted-foreground/70 text-center mt-2">
            {t("copyright", { year: new Date().getFullYear() })}
          </p>
        </div>
      </div>
    </footer>
  );
}
