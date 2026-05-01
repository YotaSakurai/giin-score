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

export interface BillSponsorDetail {
  bill_id: number;
  title: string;
  sponsor_type: string;
  co_sponsors: number;
  weight: number;
  score: number;
}

export interface LegislativeActivityBreakdown {
  bill_score: number;
  committee_score: number;
  written_questions_score: number;
  bills_sponsored: BillSponsorDetail[];
  speech_count: number;
  total_speech_chars: number;
  avg_speech_chars: number;
  density_factor: number;
  written_questions: number;
  written_questions_answered: number;
}

export interface VotingBehaviorBreakdown {
  votes_cast: number;
  vote_opportunities: number;
  participation_rate: number;
  absent_count: number;
  abstain_count: number;
  aye_count: number;
  nay_count: number;
  aye_rate: number;
  nay_rate: number;
}

export interface EnactedBillDetail {
  bill_id: number;
  title: string;
  kind_weight: number;
}

export interface PolicyInfluenceBreakdown {
  enacted_bills: EnactedBillDetail[];
  enacted_score: number;
  enacted_count: number;
  written_questions_answered: number;
  written_questions_influence: number;
}

export interface TransparencyBreakdown {
  member_meetings: number;
  total_meetings: number;
  diversity_rate: number;
}

export interface QuestionQualityBreakdown {
  avg_quality: number;
  analyzed_speeches: number;
}

export interface ScoreBreakdownData {
  legislative_activity: LegislativeActivityBreakdown;
  voting_behavior: VotingBehaviorBreakdown;
  policy_influence: PolicyInfluenceBreakdown;
  transparency: TransparencyBreakdown;
  question_quality: QuestionQualityBreakdown;
}

export interface Score {
  id: number;
  member_id: number;
  session_id: number;
  legislative_activity_raw: number;
  voting_behavior_raw: number;
  policy_influence_raw: number;
  transparency_raw: number;
  question_quality_raw: number;
  legislative_activity: number;
  voting_behavior: number;
  policy_influence: number;
  transparency: number;
  question_quality: number;
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
    question_quality: number;
  } | null;
}

export interface ScoreDetail extends Score {
  session_number: number | null;
}

export interface SpeechQualityItem {
  id: number;
  speech_id: number;
  meeting_name: string | null;
  speech_date: string | null;
  speech_chars: number;
  policy_relevance: number;
  constructiveness: number;
  expertise: number;
  national_interest: number;
  overall_quality: number;
  analysis_summary: string | null;
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

export interface DissentDetail {
  bill_title: string | null;
  member_vote: string;
  party_majority_vote: string;
}

export interface VotePattern {
  member_id: number;
  total_votes: number;
  party_majority_votes: number;
  dissent_votes: number;
  dissent_rate: number;
  absent_count: number;
  participation_rate: number;
  dissent_details: DissentDetail[];
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
  average_question_quality: number;
  grade_distribution: Record<string, number>;
}

export interface PartyStatsResponse {
  items: PartyStatsEntry[];
  chamber: string | null;
  session_number: number | null;
}

export interface WrittenQuestionItem {
  id: number;
  session_id: number;
  question_number: number;
  title: string;
  submitted_date: string | null;
  answer_date: string | null;
  question_url: string | null;
  answer_url: string | null;
  has_answer: boolean;
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

export interface MemberScorePoint {
  id: number;
  name: string;
  party: string | null;
  chamber: string;
  grade: string;
  total: number;
  legislative_activity: number;
  voting_behavior: number;
  policy_influence: number;
  transparency: number;
  question_quality: number;
}

export const AXIS_LABELS: Record<string, string> = {
  legislative_activity: "立法活動",
  voting_behavior: "投票行動",
  policy_influence: "政策影響力",
  transparency: "透明性",
  question_quality: "質問品質",
};

export const AXIS_DESCRIPTIONS: Record<string, string> = {
  legislative_activity: "発言回数・法案発議・委員会活動など立法プロセスへの参加度合い",
  voting_behavior: "本会議投票への参加率・独自判断の有無",
  policy_influence: "発議法案の成立数・質問主意書の政策影響度",
  transparency: "委員会への参加多様性・情報公開への貢献",
  question_quality: "国会質問の具体性・建設性をAIで分析した品質スコア",
};

export interface ReviewResponse {
  id: number;
  member_id: number;
  reviewer_id: string;
  display_name: string | null;
  legislative_activity: number;
  voting_behavior: number;
  policy_influence: number;
  transparency: number;
  question_quality: number;
  total: number;
  comment: string | null;
  like_count: number;
  is_liked: boolean;
  created_at: string;
  updated_at: string;
}

export interface ReviewSummary {
  member_id: number;
  review_count: number;
  average_legislative_activity: number;
  average_voting_behavior: number;
  average_policy_influence: number;
  average_transparency: number;
  average_question_quality: number;
  average_total: number;
}

export interface PartyTrendPoint {
  average_score: number;
  member_count: number;
  average_legislative_activity: number;
  average_voting_behavior: number;
  average_policy_influence: number;
  average_transparency: number;
  average_question_quality: number;
}

export interface PartyTrendSession {
  session_number: number;
  parties: Record<string, PartyTrendPoint>;
}

export interface PartyTrendResponse {
  sessions: PartyTrendSession[];
  chamber: string | null;
}

export interface ScoreMoverEntry {
  member: Member;
  current_score: number;
  previous_score: number;
  diff: number;
  current_grade: string;
  previous_grade: string;
}

export interface ScoreMoversResponse {
  risers: ScoreMoverEntry[];
  fallers: ScoreMoverEntry[];
  chamber: string | null;
}

export const SCORE_AXIS_OPTIONS: { value: string; label: string }[] = [
  { value: "total", label: "総合スコア" },
  { value: "legislative_activity", label: "立法活動" },
  { value: "voting_behavior", label: "投票行動" },
  { value: "policy_influence", label: "政策影響力" },
  { value: "transparency", label: "透明性" },
  { value: "question_quality", label: "質問品質" },
];
