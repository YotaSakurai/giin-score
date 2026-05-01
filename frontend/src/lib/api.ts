import type {
  MemberWithScore,
  MemberDetail,
  ScoreDetail,
  Bill,
  BillDetail,
  RankingEntry,
  Stats,
  PaginatedResponse,
  VoteRecord,
  DietSession,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

async function fetchApi<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

/** SWR用のfetcher関数。キーはAPI_BASE相対パス文字列 */
export async function swrFetcher<T>(path: string): Promise<T> {
  return fetchApi<T>(path);
}

/** URLSearchParamsを組み立てるヘルパー */
export function buildQuery(params?: Record<string, string | number | undefined>): string {
  if (!params) return "";
  const query = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== "") query.set(k, String(v));
  });
  const qs = query.toString();
  return qs ? `?${qs}` : "";
}

export async function getMembers(params?: {
  chamber?: string;
  party?: string;
  role_category?: string;
  search?: string;
  sort_by?: string;
  page?: number;
  per_page?: number;
}): Promise<PaginatedResponse<MemberWithScore>> {
  const query = new URLSearchParams();
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== "") query.set(k, String(v));
    });
  }
  return fetchApi(`/members?${query}`);
}

export async function getMember(id: number): Promise<MemberDetail> {
  return fetchApi(`/members/${id}`);
}

export async function getMemberScores(id: number): Promise<ScoreDetail[]> {
  return fetchApi(`/members/${id}/scores`);
}

export async function getMemberSpeeches(
  id: number,
  page = 1,
  perPage = 20
): Promise<PaginatedResponse<Record<string, unknown>>> {
  return fetchApi(`/members/${id}/speeches?page=${page}&per_page=${perPage}`);
}

export async function getMemberVotes(
  id: number,
  page = 1,
  perPage = 20
): Promise<PaginatedResponse<VoteRecord>> {
  return fetchApi(`/members/${id}/votes?page=${page}&per_page=${perPage}`);
}

export async function getBills(params?: {
  session_number?: number;
  bill_kind?: string;
  status?: string;
  search?: string;
  page?: number;
  per_page?: number;
}): Promise<PaginatedResponse<Bill>> {
  const query = new URLSearchParams();
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== "") query.set(k, String(v));
    });
  }
  return fetchApi(`/bills?${query}`);
}

export async function getBill(id: number): Promise<BillDetail> {
  return fetchApi(`/bills/${id}`);
}

export async function getRanking(params?: {
  chamber?: string;
  party?: string;
  session_number?: number;
  sort_by?: string;
  limit?: number;
  offset?: number;
}): Promise<{ items: RankingEntry[]; total: number }> {
  const query = new URLSearchParams();
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== "") query.set(k, String(v));
    });
  }
  return fetchApi(`/scores/ranking?${query}`);
}

export async function getStats(params?: {
  chamber?: string;
  session_number?: number;
}): Promise<Stats> {
  const query = new URLSearchParams();
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== "") query.set(k, String(v));
    });
  }
  return fetchApi(`/scores/stats?${query}`);
}

export async function getSessions(): Promise<DietSession[]> {
  return fetchApi("/sessions");
}

export async function postApi<T>(path: string, body: unknown): Promise<T> {
  return fetchApi<T>(path, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function putApi<T>(path: string, body: unknown): Promise<T> {
  return fetchApi<T>(path, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export async function deleteApi<T>(path: string): Promise<T> {
  return fetchApi<T>(path, { method: "DELETE" });
}
