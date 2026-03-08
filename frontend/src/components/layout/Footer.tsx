"use client";

import { useTranslations } from "next-intl";

export function Footer() {
  const t = useTranslations("footer");

  return (
    <footer className="border-t bg-muted/50 mt-auto">
      <div className="mx-auto max-w-7xl px-4 py-6">
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
