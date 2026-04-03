"use client";

import { LayoutGrid, Table2, ScatterChart } from "lucide-react";
import { cn } from "@/lib/utils";

export type ViewMode = "grid" | "table" | "scatter";

interface ViewModeToggleProps {
  value: ViewMode;
  onChange: (mode: ViewMode) => void;
}

const modes: { value: ViewMode; icon: typeof LayoutGrid; label: string }[] = [
  { value: "grid", icon: LayoutGrid, label: "カード" },
  { value: "table", icon: Table2, label: "テーブル" },
  { value: "scatter", icon: ScatterChart, label: "散布図" },
];

export function ViewModeToggle({ value, onChange }: ViewModeToggleProps) {
  return (
    <div className="inline-flex rounded-lg border border-border bg-muted p-0.5">
      {modes.map((mode) => {
        const Icon = mode.icon;
        const active = value === mode.value;
        return (
          <button
            key={mode.value}
            onClick={() => onChange(mode.value)}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
              active
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            )}
            title={mode.label}
          >
            <Icon className="size-4" />
            <span className="hidden sm:inline">{mode.label}</span>
          </button>
        );
      })}
    </div>
  );
}
