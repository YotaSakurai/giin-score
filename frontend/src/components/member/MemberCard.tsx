import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CHAMBER_LABELS, GRADE_COLORS } from "@/lib/types";
import type { MemberWithScore } from "@/lib/types";

interface MemberCardProps {
  member: MemberWithScore;
}

export function MemberCard({ member }: MemberCardProps) {
  const score = member.latest_score;
  const gradeColor = score ? GRADE_COLORS[score.grade] : "bg-gray-300";

  return (
    <Link href={`/members/${member.id}`}>
      <Card className="hover:shadow-md transition-shadow cursor-pointer h-full">
        <CardContent className="p-4">
          <div className="flex items-start justify-between mb-2">
            <div>
              <h3 className="font-bold text-foreground">{member.name}</h3>
              <p className="text-xs text-muted-foreground">{member.party ?? "無所属"}</p>
            </div>
            {score && (
              <div className={`flex h-10 w-10 items-center justify-center rounded-full text-white font-bold text-sm ${gradeColor}`}>
                {score.grade}
              </div>
            )}
          </div>
          <div className="flex gap-2 mb-3">
            <Badge variant="outline" className="text-xs">
              {CHAMBER_LABELS[member.chamber] ?? member.chamber}
            </Badge>
            {member.district && (
              <Badge variant="secondary" className="text-xs">
                {member.district}
              </Badge>
            )}
          </div>
          {score && (
            <div className="space-y-1">
              {[
                { label: "立法", value: score.legislative_activity },
                { label: "投票", value: score.voting_behavior },
                { label: "影響", value: score.policy_influence },
                { label: "透明", value: score.transparency },
              ].map(({ label, value }) => (
                <div key={label} className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground w-8">{label}</span>
                  <div className="flex-1 h-1.5 rounded-full bg-muted">
                    <div
                      className="h-1.5 rounded-full bg-blue-500"
                      style={{ width: `${Math.min(value, 100)}%` }}
                    />
                  </div>
                  <span className="text-xs text-muted-foreground w-8 text-right">{value.toFixed(0)}</span>
                </div>
              ))}
              <p className="text-right text-sm font-bold text-foreground mt-1">
                総合: {score.total.toFixed(1)}
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </Link>
  );
}
