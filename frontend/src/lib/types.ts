export interface Member {
  id: number;
  name: string;
  name_reading: string | null;
  chamber: "representatives" | "councillors";
  party: string | null;
  faction: string | null;
  district: string | null;
  role_category: string | null;
}

export interface LegislativeActivityBreakdown {
  bill_score: number;
  committee_score: number;
  speech_count: number;
  avg_speech_chars: number;
}

export interface VotingBehaviorBreakdown {
  votes_cast: number;
  vote_opportunities: number;
  participation_rate: number;
}

export interface PolicyInfluenceBreakdown {
  enacted_count: number;
  enacted_score: number;
}

export interface TransparencyBreakdown {
  committee_speeches: number;
  committee_meetings: number;
  disclosure_rate: number;
}

export interface ScoreBreakdownData {
  legislative_activity: LegislativeActivityBreakdown;
  voting_behavior: VotingBehaviorBreakdown;
  policy_influence: PolicyInfluenceBreakdown;
  transparency: TransparencyBreakdown;
}

export interface Score {
  id: number;
  member_id: number;
  session_id: number;
  legislative_activity_raw: number;
  voting_behavior_raw: number;
  policy_influence_raw: number;
  transparency_raw: number;
  legislative_activity: number;
  voting_behavior: number;
  policy_influence: number;
  transparency: number;
  total: number;
  grade: string;
  breakdown: ScoreBreakdownData | null;
}

export interface SpeechItem {
  id: number;
  speech_date: string | null;
  meeting_name: string | null;
  speech_chars: number;
  speech_url: string | null;
}

export interface MemberWithScore extends Member {
  latest_score: {
    total: number;
    grade: string;
    legislative_activity: number;
    voting_behavior: number;
    policy_influence: number;
    transparency: number;
  } | null;
}

export interface ScoreDetail extends Score {
  session_number: number | null;
}

export interface MemberDetail extends Member {
  scores: ScoreDetail[];
}

export interface Bill {
  id: number;
  session_id: number;
  bill_kind: string;
  bill_number: string | null;
  title: string;
  status: string | null;
  result: string | null;
  proposer_type: string | null;
  url: string | null;
}

export interface BillSponsor {
  member_id: number;
  member_name: string;
  sponsor_type: string;
}

export interface VoteResultSummary {
  id: number;
  chamber: string;
  ayes: number;
  nays: number;
  result: string | null;
}

export interface BillDetail extends Bill {
  sponsors: BillSponsor[];
  vote_results: VoteResultSummary[];
}

export interface VoteRecord {
  id: number;
  vote_result_id: number;
  member_id: number;
  member_name: string | null;
  vote: string;
  bill_title: string | null;
}

export interface RankingEntry {
  rank: number;
  member: Member;
  score: Score;
}

export interface ScoreDistribution {
  grade: string;
  count: number;
  percentage: number;
}

export interface Stats {
  total_members: number;
  average_score: number;
  median_score: number;
  max_score: number;
  min_score: number;
  distribution: ScoreDistribution[];
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface DietSession {
  id: number;
  session_number: number;
  kind: string;
  start_date: string | null;
  end_date: string | null;
}

export interface PartyStatsEntry {
  party: string;
  member_count: number;
  average_score: number;
  median_score: number;
  max_score: number;
  min_score: number;
  average_legislative_activity: number;
  average_voting_behavior: number;
  average_policy_influence: number;
  average_transparency: number;
}

export interface PartyStatsResponse {
  items: PartyStatsEntry[];
  chamber: string | null;
  session_number: number | null;
}

export const CHAMBER_LABELS: Record<string, string> = {
  representatives: "衆議院",
  councillors: "参議院",
};

export const GRADE_COLORS: Record<string, string> = {
  A: "bg-emerald-500",
  B: "bg-blue-500",
  C: "bg-yellow-500",
  D: "bg-orange-500",
  F: "bg-red-500",
};

export const AXIS_LABELS: Record<string, string> = {
  legislative_activity: "立法活動",
  voting_behavior: "投票行動",
  policy_influence: "政策影響力",
  transparency: "透明性",
};
