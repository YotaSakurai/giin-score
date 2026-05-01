"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { usePathname } from "next/navigation";
import { Link } from "@/i18n/navigation";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { ThemeToggle } from "@/components/ThemeToggle";
import { LocaleSwitcher } from "@/components/LocaleSwitcher";
import { QuickSearch } from "@/components/layout/QuickSearch";

const navKeys = [
  { href: "/", key: "ranking" },
  { href: "/members", key: "members" },
  { href: "/parties", key: "parties" },
  { href: "/compare", key: "compare" },
  { href: "/quality-ranking", key: "quality" },
  { href: "/favorites", key: "favorites" },
  { href: "/bills", key: "bills" },
  { href: "/about", key: "about" },
  { href: "/api-docs", key: "api" },
] as const;

export function Header() {
  const [open, setOpen] = useState(false);
  const t = useTranslations("nav");
  const pathname = usePathname();

  // パスが /ja/members/123 のような場合、/members にマッチさせる
  const isActive = (href: string) => {
    // ロケールプレフィックスを除去して比較
    const stripped = pathname.replace(/^\/(ja|en)/, "") || "/";
    if (href === "/") return stripped === "/";
    return stripped.startsWith(href);
  };

  return (
    <header className="sticky top-0 z-50 border-b bg-background/95 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4">
        <Link href="/" className="flex items-center gap-2 font-bold text-lg text-foreground">
          <span className="text-blue-600 dark:text-blue-400">GiinScore</span>
        </Link>

        <nav aria-label="メインナビゲーション" className="hidden md:flex items-center gap-6">
          {navKeys.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`text-sm font-medium transition-colors ${
                isActive(item.href)
                  ? "text-foreground border-b-2 border-blue-600 pb-0.5"
                  : "text-muted-foreground hover:text-foreground"
              }`}
              aria-current={isActive(item.href) ? "page" : undefined}
            >
              {t(item.key)}
            </Link>
          ))}
          <QuickSearch />
          <LocaleSwitcher />
          <ThemeToggle />
        </nav>

        <div className="flex items-center gap-2 md:hidden">
          <LocaleSwitcher />
          <ThemeToggle />
          <Sheet open={open} onOpenChange={setOpen}>
            <SheetTrigger asChild>
              <Button variant="ghost" size="sm" aria-label={t("openMenu")}>
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              </Button>
            </SheetTrigger>
            <SheetContent side="right" className="w-64">
              <nav aria-label="モバイルナビゲーション" className="flex flex-col gap-4 mt-8">
                {navKeys.map((item) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`text-base font-medium ${
                      isActive(item.href)
                        ? "text-primary font-bold"
                        : "text-foreground/80 hover:text-primary"
                    }`}
                    onClick={() => setOpen(false)}
                    aria-current={isActive(item.href) ? "page" : undefined}
                  >
                    {t(item.key)}
                  </Link>
                ))}
              </nav>
            </SheetContent>
          </Sheet>
        </div>
      </div>
    </header>
  );
}
