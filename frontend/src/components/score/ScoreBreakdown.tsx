import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AXIS_LABELS, AXIS_DESCRIPTIONS } from "@/lib/types";
import type {
  ScoreBreakdownData,
  LegislativeActivityBreakdown,
  VotingBehaviorBreakdown,
  PolicyInfluenceBreakdown,
  TransparencyBreakdown,
  QuestionQualityBreakdown,
} from "@/lib/types";

interface ScoreBreakdownProps {
  breakdown: ScoreBreakdownData | null;
  scores: {
    legislative_activity: number;
    voting_behavior: number;
    policy_influence: number;
    transparency: number;
    question_quality: number;
  };
}

function MiniBar({ value, max = 100, color = "bg-blue-500" }: { value: number; max?: number; color?: string }) {
  const pct = Math.min((value / max) * 100, 100);
  return (
    <div className="h-1.5 w-16 rounded-full bg-muted inline-block align-middle ml-2">
      <div className={`h-1.5 rounded-full ${color}`} style={{ width: `${pct}%` }} />
    </div>
  );
}

function Stat({ label, value, unit, bar, barMax, barColor }: {
  label: string;
  value: string | number;
  unit?: string;
  bar?: number;
  barMax?: number;
  barColor?: string;
}) {
  return (
    <div className="flex items-center justify-between py-0.5">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className="text-xs font-medium">
        {value}{unit && <span className="text-muted-foreground ml-0.5">{unit}</span>}
        {bar !== undefined && <MiniBar value={bar} max={barMax} color={barColor} />}
      </span>
    </div>
  );
}

function LegislativeDetail({ d, enactedCount }: { d: LegislativeActivityBreakdown; enactedCount?: number }) {
  const sponsoredCount = d.bills_sponsored?.length ?? 0;
  const enacted = enactedCount ?? 0;
  return (
    <div className="space-y-0.5">
      <Stat label="発言回数" value={d.speech_count} unit="回" />
      <Stat label="平均発言文字数" value={d.avg_speech_chars?.toLocaleString() ?? 0} unit="字" />
      <Stat label="発言密度係数" value={d.density_factor?.toFixed(2) ?? "0"} />
      <Stat label="法案発議スコア" value={d.bill_score?.toFixed(1) ?? "0"} />
      <Stat label="委員会活動スコア" value={d.committee_score?.toFixed(1) ?? "0"} />
      {(d.written_questions > 0) && (
        <>
          <Stat label="質問主意書" value={d.written_questions} unit="件" />
          <Stat label="答弁あり" value={d.written_questions_answered} unit="件" />
        </>
      )}
      {/* 発議 vs 成立 比率バー */}
      {sponsoredCount > 0 && (
        <div className="mt-2 rounded-lg border p-2 bg-muted/30">
          <div className="flex items-center justify-between text-xs mb-1">
            <span className="text-muted-foreground">発議 {sponsoredCount}件 → 成立 {enacted}件</span>
            <span className="font-medium">
              {sponsoredCount > 0 ? `${((enacted / sponsoredCount) * 100).toFixed(0)}%` : "0%"} 成立率
            </span>
          </div>
          <div className="h-3 rounded-full bg-muted flex overflow-hidden">
            {enacted > 0 && (
              <div
                className="h-3 bg-emerald-500 rounded-l"
                style={{ width: `${(enacted / sponsoredCount) * 100}%` }}
                title={`成立: ${enacted}件`}
              />
            )}
            <div
              className="h-3 bg-orange-300"
              style={{ width: `${((sponsoredCount - enacted) / sponsoredCount) * 100}%` }}
              title={`未成立: ${sponsoredCount - enacted}件`}
            />
          </div>
          <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
            <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-emerald-500" />成立</span>
            <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-orange-300" />未成立</span>
          </div>
        </div>
      )}
      {d.bills_sponsored?.length > 0 && (
        <div className="mt-2">
          <p className="text-xs font-medium text-muted-foreground mb-1">発議法案:</p>
          <ul className="space-y-1 ml-2">
            {d.bills_sponsored.slice(0, 5).map((b) => (
              <li key={b.bill_id} className="text-xs text-muted-foreground">
                <span className="text-foreground">{b.title}</span>
                <span className="ml-1 text-muted-foreground/70">
                  ({b.sponsor_type === "primary" ? "筆頭" : `共同(${b.co_sponsors}名)`}, 重み{b.weight.toFixed(1)})
                </span>
              </li>
            ))}
            {d.bills_sponsored.length > 5 && (
              <li className="text-xs text-muted-foreground/70">他{d.bills_sponsored.length - 5}件</li>
            )}
          </ul>
        </div>
      )}
    </div>
  );
}

function VotingDetail({ d }: { d: VotingBehaviorBreakdown }) {
  return (
    <div className="space-y-0.5">
      <Stat
        label="投票参加率"
        value={d.participation_rate?.toFixed(1) ?? "0"}
        unit="%"
        bar={d.participation_rate}
        barColor="bg-blue-500"
      />
      <Stat label="投票回数" value={`${d.votes_cast} / ${d.vote_opportunities}`} unit="回" />
      <Stat label="賛成" value={d.aye_count} unit={`回 (${d.aye_rate?.toFixed(1) ?? 0}%)`} />
      <Stat label="反対" value={d.nay_count} unit={`回 (${d.nay_rate?.toFixed(1) ?? 0}%)`} />
      {d.abstain_count > 0 && <Stat label="棄権" value={d.abstain_count} unit="回" />}
      {d.absent_count > 0 && <Stat label="欠席" value={d.absent_count} unit="回" />}
    </div>
  );
}

function PolicyDetail({ d }: { d: PolicyInfluenceBreakdown }) {
  return (
    <div className="space-y-0.5">
      <Stat label="成立法案数" value={d.enacted_count} unit="件" />
      <Stat label="成立法案スコア" value={d.enacted_score?.toFixed(1) ?? "0"} />
      {d.written_questions_answered > 0 && (
        <>
          <Stat label="答弁付き質問主意書" value={d.written_questions_answered} unit="件" />
          <Stat label="質問主意書影響度" value={d.written_questions_influence?.toFixed(1) ?? "0"} />
        </>
      )}
      {d.enacted_bills?.length > 0 && (
        <div className="mt-2">
          <p className="text-xs font-medium text-muted-foreground mb-1">成立法案:</p>
          <ul className="space-y-1 ml-2">
            {d.enacted_bills.map((b) => (
              <li key={b.bill_id} className="text-xs text-muted-foreground">
                <span className="text-foreground">{b.title}</span>
                <span className="ml-1 text-muted-foreground/70">(重み{b.kind_weight.toFixed(1)})</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function TransparencyDetail({ d }: { d: TransparencyBreakdown }) {
  return (
    <div className="space-y-0.5">
      <Stat
        label="委員会多様性"
        value={d.diversity_rate?.toFixed(1) ?? "0"}
        unit="%"
        bar={d.diversity_rate}
        barMax={30}
        barColor="bg-emerald-500"
      />
      <Stat label="参加委員会数" value={`${d.member_meetings} / ${d.total_meetings}`} unit="種" />
    </div>
  );
}

function QualityDetail({ d }: { d: QuestionQualityBreakdown }) {
  return (
    <div className="space-y-0.5">
      <Stat
        label="平均質問品質"
        value={d.avg_quality?.toFixed(1) ?? "0"}
        unit="/100"
        bar={d.avg_quality}
        barColor="bg-violet-500"
      />
      <Stat label="分析済み発言数" value={d.analyzed_speeches} unit="件" />
    </div>
  );
}

const AXIS_COLORS: Record<string, string> = {
  legislative_activity: "bg-blue-500",
  voting_behavior: "bg-cyan-500",
  policy_influence: "bg-amber-500",
  transparency: "bg-emerald-500",
  question_quality: "bg-violet-500",
};

export function ScoreBreakdown({ breakdown, scores }: ScoreBreakdownProps) {
  const axes = [
    { key: "legislative_activity" as const, score: scores.legislative_activity },
    { key: "voting_behavior" as const, score: scores.voting_behavior },
    { key: "policy_influence" as const, score: scores.policy_influence },
    { key: "transparency" as const, score: scores.transparency },
    { key: "question_quality" as const, score: scores.question_quality },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">スコア内訳</CardTitle>
        <p className="text-xs text-muted-foreground">
          各スコアはグループ内パーセンタイルランク（0-100）で正規化されています
        </p>
      </CardHeader>
      <CardContent className="space-y-5">
        {axes.map(({ key, score }) => {
          const color = AXIS_COLORS[key];
          return (
            <div key={key}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium text-foreground/80" title={AXIS_DESCRIPTIONS[key]}>
                  {AXIS_LABELS[key]}
                  <abbr className="no-underline text-muted-foreground/60 ml-0.5 cursor-help" title={AXIS_DESCRIPTIONS[key]}>ⓘ</abbr>
                </span>
                <span className="text-sm font-bold text-foreground">{score.toFixed(1)}</span>
              </div>
              <div
                className="h-2 w-full rounded-full bg-muted"
                role="progressbar"
                aria-valuenow={Math.round(score)}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label={`${AXIS_LABELS[key]} ${score.toFixed(1)}点`}
              >
                <div
                  className={`h-2 rounded-full ${color} transition-all`}
                  style={{ width: `${Math.min(score, 100)}%` }}
                />
              </div>
              {breakdown?.[key] && (
                <div className="mt-2 ml-1 border-l-2 border-muted pl-3">
                  {key === "legislative_activity" && (
                    <LegislativeDetail
                      d={breakdown.legislative_activity}
                      enactedCount={breakdown.policy_influence?.enacted_count}
                    />
                  )}
                  {key === "voting_behavior" && (
                    <VotingDetail d={breakdown.voting_behavior} />
                  )}
                  {key === "policy_influence" && (
                    <PolicyDetail d={breakdown.policy_influence} />
                  )}
                  {key === "transparency" && (
                    <TransparencyDetail d={breakdown.transparency} />
                  )}
                  {key === "question_quality" && (
                    <QualityDetail d={breakdown.question_quality} />
                  )}
                </div>
              )}
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
