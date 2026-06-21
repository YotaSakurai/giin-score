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
import {
  Trophy, Users, Building2, GitCompareArrows, MessageSquareText,
  Star, FileText, Info, Code,
} from "lucide-react";

const navKeys = [
  { href: "/", key: "ranking", icon: Trophy },
  { href: "/members", key: "members", icon: Users },
  { href: "/parties", key: "parties", icon: Building2 },
  { href: "/compare", key: "compare", icon: GitCompareArrows },
  { href: "/quality-ranking", key: "quality", icon: MessageSquareText },
  { href: "/favorites", key: "favorites", icon: Star },
  { href: "/bills", key: "bills", icon: FileText },
  { href: "/about", key: "about", icon: Info },
  { href: "/api-docs", key: "api", icon: Code },
] as const;

export function Header() {
  const [open, setOpen] = useState(false);
  const t = useTranslations("nav");
  const pathname = usePathname();

  const isActive = (href: string) => {
    const stripped = pathname.replace(/^\/(ja|en)/, "") || "/";
    if (href === "/") return stripped === "/";
    return stripped.startsWith(href);
  };

  return (
    <header className="sticky top-0 z-50 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4">
        <Link href="/" className="flex items-center gap-2 font-bold text-lg text-foreground group">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 dark:bg-blue-500 text-white text-sm font-black transition-transform group-hover:scale-105">
            G
          </div>
          <span className="hidden sm:inline text-blue-600 dark:text-blue-400">GiinScore</span>
        </Link>

        <nav aria-label="メインナビゲーション" className="hidden lg:flex items-center gap-1">
          {navKeys.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`relative flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm font-medium transition-colors ${
                  active
                    ? "text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/40"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                }`}
                aria-current={active ? "page" : undefined}
              >
                <Icon className="h-3.5 w-3.5" aria-hidden="true" />
                {t(item.key)}
              </Link>
            );
          })}
          <div className="ml-2 flex items-center gap-1.5">
            <QuickSearch />
            <LocaleSwitcher />
            <ThemeToggle />
          </div>
        </nav>

        <div className="flex items-center gap-2 lg:hidden">
          <QuickSearch />
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
            <SheetContent side="right" className="w-72">
              <nav aria-label="モバイルナビゲーション" className="flex flex-col gap-1 mt-8">
                {navKeys.map((item) => {
                  const Icon = item.icon;
                  const active = isActive(item.href);
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                        active
                          ? "bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 border-l-3 border-blue-600"
                          : "text-foreground/80 hover:text-foreground hover:bg-muted/50"
                      }`}
                      onClick={() => setOpen(false)}
                      aria-current={active ? "page" : undefined}
                    >
                      <Icon className={`h-4 w-4 ${active ? "text-blue-600 dark:text-blue-400" : "text-muted-foreground"}`} aria-hidden="true" />
                      {t(item.key)}
                    </Link>
                  );
                })}
              </nav>
            </SheetContent>
          </Sheet>
        </div>
      </div>
    </header>
  );
}
