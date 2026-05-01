import { Card, CardContent } from "@/components/ui/card";
import { GRADE_COLORS } from "@/lib/types";
import { GRADE_DESCRIPTIONS } from "@/lib/constants";

interface ScoreCardProps {
  total: number;
  grade: string;
  label?: string;
}

export function ScoreCard({ total, grade, label }: ScoreCardProps) {
  const colorClass = GRADE_COLORS[grade] || "bg-gray-400";
  const gradeHint = GRADE_DESCRIPTIONS[grade]?.split("—")[0]?.trim();

  return (
    <Card>
      <CardContent className="flex items-center gap-4 p-4" aria-label={`${label ?? "スコア"}: ${total.toFixed(1)}点, グレード${grade}`}>
        <div
          className={`flex h-14 w-14 items-center justify-center rounded-full text-white font-bold text-xl ${colorClass}`}
          role="img"
          aria-label={`グレード ${grade}`}
        >
          {grade}
        </div>
        <div>
          {label && <p className="text-xs text-muted-foreground">{label}</p>}
          <p className="text-2xl font-bold text-foreground">{total.toFixed(1)}</p>
          <p className="text-xs text-muted-foreground">/ 100</p>
          {gradeHint && (
            <p className="text-[10px] text-muted-foreground/70 mt-0.5">{gradeHint}</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
