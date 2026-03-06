import { Card, CardContent } from "@/components/ui/card";
import { GRADE_COLORS } from "@/lib/types";

interface ScoreCardProps {
  total: number;
  grade: string;
  label?: string;
}

export function ScoreCard({ total, grade, label }: ScoreCardProps) {
  const colorClass = GRADE_COLORS[grade] || "bg-gray-400";

  return (
    <Card>
      <CardContent className="flex items-center gap-4 p-4">
        <div className={`flex h-14 w-14 items-center justify-center rounded-full text-white font-bold text-xl ${colorClass}`}>
          {grade}
        </div>
        <div>
          {label && <p className="text-xs text-muted-foreground">{label}</p>}
          <p className="text-2xl font-bold text-foreground">{total.toFixed(1)}</p>
          <p className="text-xs text-muted-foreground">/ 100</p>
        </div>
      </CardContent>
    </Card>
  );
}
