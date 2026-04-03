import useSWR from "swr";
import { swrFetcher, buildQuery } from "./api";
import type {
  RankingEntry,
  Stats,
  MemberWithScore,
  MemberDetail,
  MemberScorePoint,
  Bill,
  BillDetail,
  PaginatedResponse,
  SpeechItem,
  SpeechQualityItem,
  VoteRecord,
  VotePattern,
  PartyStatsResponse,
} from "./types";

// ---- ランキング ----
export function useRanking(params?: {
  chamber?: string;
  party?: string;
  session_number?: number;
  sort_by?: string;
  limit?: number;
  offset?: number;
}) {
  const key = `/scores/ranking${buildQuery(params)}`;
  return useSWR<{ items: RankingEntry[]; total: number }>(key, swrFetcher);
}

// ---- 統計 ----
export function useStats(params?: {
  chamber?: string;
  session_number?: number;
}) {
  const key = `/scores/stats${buildQuery(params)}`;
  return useSWR<Stats>(key, swrFetcher);
}

// ---- 議員一覧 ----
export function useMembers(params?: {
  chamber?: string;
  party?: string;
  role_category?: string;
  search?: string;
  district?: string;
  grade?: string;
  score_min?: number;
  score_max?: number;
  la_min?: number;
  la_max?: number;
  vb_min?: number;
  vb_max?: number;
  pi_min?: number;
  pi_max?: number;
  tr_min?: number;
  tr_max?: number;
  qq_min?: number;
  qq_max?: number;
  sort_by?: string;
  sort_order?: string;
  page?: number;
  per_page?: number;
}) {
  const key = `/members${buildQuery(params)}`;
  return useSWR<PaginatedResponse<MemberWithScore>>(key, swrFetcher);
}

// ---- 散布図用データ ----
export function useMembersScatter(params?: {
  chamber?: string;
  party?: string;
  search?: string;
  district?: string;
  grade?: string;
  score_min?: number;
  score_max?: number;
  la_min?: number;
  la_max?: number;
  vb_min?: number;
  vb_max?: number;
  pi_min?: number;
  pi_max?: number;
  tr_min?: number;
  tr_max?: number;
  qq_min?: number;
  qq_max?: number;
}) {
  const key = `/members/scatter${buildQuery(params)}`;
  return useSWR<MemberScorePoint[]>(key, swrFetcher);
}

// ---- 議員詳細 ----
export function useMember(id: number) {
  const key = `/members/${id}`;
  return useSWR<MemberDetail>(key, swrFetcher);
}

// ---- 議員発言 ----
export function useMemberSpeeches(id: number, page = 1, perPage = 10) {
  const key = `/members/${id}/speeches${buildQuery({ page, per_page: perPage })}`;
  return useSWR<PaginatedResponse<SpeechItem>>(key, swrFetcher);
}

// ---- 議員投票 ----
export function useMemberVotes(id: number, page = 1, perPage = 10) {
  const key = `/members/${id}/votes${buildQuery({ page, per_page: perPage })}`;
  return useSWR<PaginatedResponse<VoteRecord>>(key, swrFetcher);
}

// ---- 投票パターン ----
export function useVotePattern(id: number) {
  const key = `/members/${id}/vote-pattern`;
  return useSWR<VotePattern>(key, swrFetcher);
}

// ---- 法案一覧 ----
export function useBills(params?: {
  session_number?: number;
  bill_kind?: string;
  status?: string;
  search?: string;
  page?: number;
  per_page?: number;
}) {
  const key = `/bills${buildQuery(params)}`;
  return useSWR<PaginatedResponse<Bill>>(key, swrFetcher);
}

// ---- 法案詳細 ----
export function useBill(id: number) {
  const key = `/bills/${id}`;
  return useSWR<BillDetail>(key, swrFetcher);
}

// ---- 党派別統計 ----
export function usePartyStats(params?: {
  chamber?: string;
  session_number?: number;
}) {
  const key = `/scores/by-party${buildQuery(params)}`;
  return useSWR<PartyStatsResponse>(key, swrFetcher);
}

// ---- データ品質 ----
export function useDataQuality() {
  return useSWR<{
    total_members: number;
    total_sessions: number;
    sessions: {
      session_number: number;
      session_kind: string;
      member_count: number;
      scored_member_count: number;
      speech_count: number;
      speakers_count: number;
      bill_count: number;
      vote_result_count: number;
      vote_record_count: number;
    }[];
  }>("/data-quality", swrFetcher);
}

// ---- 発言品質 ----
export function useSpeechQuality(id: number, page = 1, perPage = 10) {
  const key = `/members/${id}/speech-quality${buildQuery({ page, per_page: perPage })}`;
  return useSWR<PaginatedResponse<SpeechQualityItem>>(key, swrFetcher);
}

// ---- 政党一覧 ----
export function useParties(chamber?: string) {
  const key = `/scores/parties${buildQuery({ chamber })}`;
  return useSWR<string[]>(key, swrFetcher);
}
