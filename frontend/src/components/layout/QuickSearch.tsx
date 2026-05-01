"use client";

import { useState, useEffect, useRef } from "react";
import useSWR from "swr";
import { swrFetcher, buildQuery } from "@/lib/api";
import type { MemberWithScore, PaginatedResponse } from "@/lib/types";
import { GRADE_COLORS } from "@/lib/types";
import { useRouter } from "next/navigation";

export function QuickSearch() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const timerRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const v = e.target.value;
    setQuery(v);
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => setDebouncedQuery(v), 300);
  };

  useEffect(() => () => clearTimeout(timerRef.current), []);

  // キーボードショートカット: / で検索フォーカス
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "/" && !e.ctrlKey && !e.metaKey) {
        const target = e.target as HTMLElement;
        if (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable) return;
        e.preventDefault();
        setOpen(true);
        inputRef.current?.focus();
      }
      if (e.key === "Escape") {
        setOpen(false);
        setQuery("");
        setDebouncedQuery("");
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, []);

  // 外部クリックで閉じる
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const { data } = useSWR<PaginatedResponse<MemberWithScore>>(
    debouncedQuery.length >= 1
      ? `/members${buildQuery({ search: debouncedQuery, per_page: 6 })}`
      : null,
    swrFetcher,
    { revalidateOnFocus: false, dedupingInterval: 1000 },
  );

  const items = data?.items ?? [];

  const handleSelect = (id: number) => {
    router.push(`/members/${id}`);
    setOpen(false);
    setQuery("");
    setDebouncedQuery("");
  };

  return (
    <div ref={containerRef} className="relative">
      {open ? (
        <input
          ref={inputRef}
          type="text"
          placeholder="議員名で検索..."
          value={query}
          onChange={handleChange}
          className="h-8 w-40 rounded-md border bg-background px-2 text-sm outline-none focus:ring-1 focus:ring-ring"
          // eslint-disable-next-line jsx-a11y/no-autofocus
          autoFocus
        />
      ) : (
        <button
          type="button"
          onClick={() => {
            setOpen(true);
            setTimeout(() => inputRef.current?.focus(), 0);
          }}
          className="flex h-8 items-center gap-1.5 rounded-md border bg-muted/50 px-2 text-sm text-muted-foreground hover:bg-muted transition-colors"
          aria-label="議員を検索"
        >
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.3-4.3" />
          </svg>
          <span className="hidden lg:inline">検索</span>
          <kbd className="hidden lg:inline ml-1 rounded border bg-background px-1 text-[10px] font-mono text-muted-foreground/70">/</kbd>
        </button>
      )}
      {open && debouncedQuery.length >= 1 && items.length > 0 && (
        <div className="absolute top-full right-0 mt-1 w-72 bg-popover border border-border rounded-lg shadow-lg z-50 max-h-80 overflow-auto">
          {items.map((m) => {
            const gc = m.latest_score ? (GRADE_COLORS[m.latest_score.grade] || "bg-gray-300") : "";
            return (
              <button
                key={m.id}
                type="button"
                className="w-full px-3 py-2 text-left hover:bg-muted/50 flex items-center gap-2 text-sm"
                onClick={() => handleSelect(m.id)}
              >
                {m.latest_score && (
                  <span className={`inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-white text-[10px] font-bold ${gc}`}>
                    {m.latest_score.grade}
                  </span>
                )}
                <div className="flex-1 min-w-0">
                  <p className="font-medium truncate">{m.name}</p>
                  <p className="text-xs text-muted-foreground">{m.party ?? "無所属"}</p>
                </div>
                {m.latest_score && (
                  <span className="text-xs text-muted-foreground shrink-0">
                    {m.latest_score.total.toFixed(1)}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      )}
      {open && debouncedQuery.length >= 1 && items.length === 0 && data && (
        <div className="absolute top-full right-0 mt-1 w-72 bg-popover border border-border rounded-lg shadow-lg z-50 p-4 text-center">
          <p className="text-sm text-muted-foreground">該当する議員が見つかりません</p>
        </div>
      )}
    </div>
  );
}
