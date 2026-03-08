"use client";

import { useLocale } from "next-intl";
import { usePathname, useRouter } from "@/i18n/navigation";
import { Button } from "@/components/ui/button";

export function LocaleSwitcher() {
  const locale = useLocale();
  const pathname = usePathname();
  const router = useRouter();

  const nextLocale = locale === "ja" ? "en" : "ja";
  const label = locale === "ja" ? "EN" : "JA";

  return (
    <Button
      variant="ghost"
      size="sm"
      className="text-xs font-medium px-2"
      onClick={() => router.replace(pathname, { locale: nextLocale })}
    >
      {label}
    </Button>
  );
}
