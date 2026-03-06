import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AXIS_LABELS } from "@/lib/types";
import type { ScoreBreakdownData } from "@/lib/types";

interface ScoreBreakdownProps {
  breakdown: ScoreBreakdownData | null;
  scores: {
    legislative_activity: number;
    voting_behavior: number;
    policy_influence: number;
    transparency: number;
  };
}

export function ScoreBreakdown({ breakdown, scores }: ScoreBreakdownProps) {
  const axes = [
    { key: "legislative_activity", score: scores.legislative_activity },
    { key: "voting_behavior", score: scores.voting_behavior },
    { key: "policy_influence", score: scores.policy_influence },
    { key: "transparency", score: scores.transparency },
  ] as const;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">スコア内訳</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {axes.map(({ key, score }) => {
          const detail = breakdown?.[key] as Record<string, unknown> | undefined;
          return (
            <div key={key}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium text-foreground/80">
                  {AXIS_LABELS[key]}
                </span>
                <span className="text-sm font-bold text-foreground">{score.toFixed(1)}</span>
              </div>
              <div className="h-2 w-full rounded-full bg-muted">
                <div
                  className="h-2 rounded-full bg-blue-500 transition-all"
                  style={{ width: `${Math.min(score, 100)}%` }}
                />
              </div>
              {detail && (
                <div className="mt-1 text-xs text-muted-foreground space-x-3">
                  {Object.entries(detail).map(([k, v]) => {
                    if (Array.isArray(v)) return null;
                    return (
                      <span key={k}>
                        {k}: {typeof v === "number" ? v.toFixed(1) : String(v)}
                      </span>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
