"use client";

import { useTranslations } from "next-intl";
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
        {lastUpdated && (
          <p className="text-xs text-muted-foreground/70 text-center mb-2">
            データ最終更新: {lastUpdated}
          </p>
        )}
        <p className="text-xs text-muted-foreground text-center leading-relaxed">
          {t("disclaimer")}
        </p>
        <p className="text-xs text-muted-foreground/70 text-center mt-2">
          {t("copyright", { year: new Date().getFullYear() })}
        </p>
      </div>
    </footer>
  );
}
