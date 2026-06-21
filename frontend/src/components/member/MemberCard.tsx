import { memo, useMemo } from "react";
import { Link } from "@/i18n/navigation";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CHAMBER_LABELS, GRADE_COLORS } from "@/lib/types";
import type { MemberWithScore } from "@/lib/types";

interface MemberCardProps {
  member: MemberWithScore;
}

/** スコアパターンから注意フラグを生成 */
function getWarningFlags(score: NonNullable<MemberWithScore["latest_score"]>): string[] {
  const flags: string[] = [];
  if (score.total < 20) {
    flags.push("活動量が非常に少ない");
  }
  if (score.voting_behavior < 20) {
    flags.push("投票参加率が低い");
  }
  if (score.legislative_activity >= 60 && score.policy_influence < 20) {
    flags.push("法案提出は多いが成立実績が少ない");
  }
  if (score.question_quality < 15 && score.legislative_activity < 15) {
    flags.push("質疑・立法とも低水準");
  }
  return flags;
}

function getBalanceInfo(score: NonNullable<MemberWithScore["latest_score"]>): { label: string; tooltip: string } {
  const vals = [score.legislative_activity, score.voting_behavior, score.policy_influence, score.transparency, score.question_quality];
  const mean = vals.reduce((a, b) => a + b) / vals.length;
  const stdDev = Math.sqrt(vals.reduce((sum, v) => sum + (v - mean) ** 2, 0) / vals.length);
  if (stdDev < 10) return { label: "バランス型", tooltip: `5軸のばらつきが小さい（σ=${stdDev.toFixed(1)}）` };
  if (stdDev < 20) return { label: "準バランス型", tooltip: `5軸にやや偏りあり（σ=${stdDev.toFixed(1)}��` };
  return { label: "特化型", tooltip: `特定の軸に集中した活動パターン（σ=${stdDev.toFixed(1)}）` };
}

export const MemberCard = memo(function MemberCard({ member }: MemberCardProps) {
  const score = member.latest_score;
  const gradeColor = score ? GRADE_COLORS[score.grade] : "bg-gray-300";
  const warnings = useMemo(() => score ? getWarningFlags(score) : [], [score]);
  const balance = useMemo(() => score ? getBalanceInfo(score) : null, [score]);

  return (
    <Link href={`/members/${member.id}`}>
      <Card className={`card-hover cursor-pointer h-full ${warnings.length > 0 ? "border-red-200 dark:border-red-900" : ""}`}>
        <CardContent className="p-4">
          <div className="flex items-start justify-between mb-2">
            <div>
              <h3 className="font-bold text-foreground">{member.name}</h3>
              <p className="text-xs text-muted-foreground">{member.party ?? "無所属"}</p>
            </div>
            {score && (
              <div className={`grade-badge flex h-10 w-10 items-center justify-center rounded-full text-white font-bold text-sm ${gradeColor}`}>
                {score.grade}
              </div>
            )}
          </div>
          <div className="flex gap-2 mb-3 flex-wrap">
            <Badge variant="outline" className="text-xs">
              {CHAMBER_LABELS[member.chamber] ?? member.chamber}
            </Badge>
            {member.district && (
              <Badge variant="secondary" className="text-xs">
                {member.district}
              </Badge>
            )}
          </div>
          {warnings.length > 0 && (
            <div className="mb-3 rounded-md bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 px-2 py-1.5">
              {warnings.map((w, i) => (
                <p key={i} className="text-xs text-red-700 dark:text-red-400 flex items-center gap-1">
                  <svg className="h-3 w-3 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                  {w}
                </p>
              ))}
            </div>
          )}
          {score && (
            <div className="space-y-1">
              {[
                { label: "立法", value: score.legislative_activity },
                { label: "投票", value: score.voting_behavior },
                { label: "影響", value: score.policy_influence },
                { label: "透明", value: score.transparency },
                { label: "質問", value: score.question_quality },
              ].map(({ label, value }) => (
                <div key={label} className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground w-8">{label}</span>
                  <div className="flex-1 h-1.5 rounded-full bg-muted">
                    <div
                      className={`h-1.5 rounded-full animate-bar-fill ${value < 20 ? "bg-red-500" : value < 40 ? "bg-orange-400" : "bg-blue-500"}`}
                      style={{ width: `${Math.min(value, 100)}%` }}
                    />
                  </div>
                  <span className="text-xs text-muted-foreground w-8 text-right">{value.toFixed(0)}</span>
                </div>
              ))}
              <div className="flex items-center justify-between mt-1">
                <span className="text-[10px] text-muted-foreground cursor-help" title={balance?.tooltip}>
                  {balance?.label}
                </span>
                <p className="text-sm font-bold text-foreground">
                  総合: {score.total.toFixed(1)}
                </p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </Link>
  );
});
