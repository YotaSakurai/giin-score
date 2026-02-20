import type { MemberWithScore, RankingEntry, Stats, Member, Score, BillDetail, MemberDetail, ScoreDetail } from "./types";

const mockMembers: MemberWithScore[] = [
  { id: 1, name: "山田太郎", name_reading: "やまだたろう", chamber: "representatives", party: "自由民主党", faction: null, district: "東京1区", role_category: "ruling_junior", latest_score: { total: 82.5, grade: "A", legislative_activity: 85, voting_behavior: 90, policy_influence: 70, transparency: 75 } },
  { id: 2, name: "佐藤花子", name_reading: "さとうはなこ", chamber: "councillors", party: "立憲民主党", faction: null, district: "比例", role_category: "opposition_senior", latest_score: { total: 74.2, grade: "B", legislative_activity: 70, voting_behavior: 85, policy_influence: 65, transparency: 80 } },
  { id: 3, name: "鈴木一郎", name_reading: "すずきいちろう", chamber: "representatives", party: "公明党", faction: null, district: "大阪5区", role_category: "ruling_junior", latest_score: { total: 68.3, grade: "B", legislative_activity: 60, voting_behavior: 75, policy_influence: 70, transparency: 65 } },
  { id: 4, name: "田中美咲", name_reading: "たなかみさき", chamber: "councillors", party: "日本維新の会", faction: null, district: "大阪府", role_category: "opposition_junior", latest_score: { total: 55.1, grade: "C", legislative_activity: 50, voting_behavior: 60, policy_influence: 45, transparency: 70 } },
  { id: 5, name: "高橋健太", name_reading: "たかはしけんた", chamber: "representatives", party: "国民民主党", faction: null, district: "神奈川3区", role_category: "opposition_junior", latest_score: { total: 91.0, grade: "A", legislative_activity: 95, voting_behavior: 88, policy_influence: 90, transparency: 85 } },
  { id: 6, name: "渡辺直美", name_reading: "わたなべなおみ", chamber: "councillors", party: "日本共産党", faction: null, district: "比例", role_category: "opposition_junior", latest_score: { total: 45.8, grade: "C", legislative_activity: 40, voting_behavior: 55, policy_influence: 35, transparency: 60 } },
  { id: 7, name: "伊藤誠", name_reading: "いとうまこと", chamber: "representatives", party: "自由民主党", faction: null, district: "愛知2区", role_category: "cabinet", latest_score: { total: 78.4, grade: "B", legislative_activity: 80, voting_behavior: 82, policy_influence: 75, transparency: 70 } },
  { id: 8, name: "小林さくら", name_reading: "こばやしさくら", chamber: "councillors", party: "れいわ新選組", faction: null, district: "比例", role_category: "opposition_junior", latest_score: { total: 62.7, grade: "B", legislative_activity: 55, voting_behavior: 70, policy_influence: 50, transparency: 80 } },
  { id: 9, name: "加藤大輔", name_reading: "かとうだいすけ", chamber: "representatives", party: "立憲民主党", faction: null, district: "埼玉4区", role_category: "opposition_senior", latest_score: { total: 35.2, grade: "D", legislative_activity: 30, voting_behavior: 40, policy_influence: 25, transparency: 50 } },
  { id: 10, name: "吉田裕子", name_reading: "よしだゆうこ", chamber: "councillors", party: "自由民主党", faction: null, district: "千葉県", role_category: "ruling_junior", latest_score: { total: 71.6, grade: "B", legislative_activity: 75, voting_behavior: 70, policy_influence: 68, transparency: 72 } },
];

export function getMockMembers(): MemberWithScore[] {
  return mockMembers;
}

export function getMockRanking(): RankingEntry[] {
  return [...mockMembers]
    .sort((a, b) => (b.latest_score?.total ?? 0) - (a.latest_score?.total ?? 0))
    .map((m, i) => ({
      rank: i + 1,
      member: m as Member,
      score: {
        id: m.id,
        member_id: m.id,
        session_id: 1,
        legislative_activity_raw: 0,
        voting_behavior_raw: 0,
        policy_influence_raw: 0,
        transparency_raw: 0,
        legislative_activity: m.latest_score?.legislative_activity ?? 0,
        voting_behavior: m.latest_score?.voting_behavior ?? 0,
        policy_influence: m.latest_score?.policy_influence ?? 0,
        transparency: m.latest_score?.transparency ?? 0,
        total: m.latest_score?.total ?? 0,
        grade: m.latest_score?.grade ?? "F",
        breakdown: null,
      } as Score,
    }));
}

export function getMockStats(): Stats {
  return {
    total_members: 700,
    average_score: 52.3,
    median_score: 48.7,
    max_score: 95.2,
    min_score: 5.1,
    distribution: [
      { grade: "A", count: 70, percentage: 10 },
      { grade: "B", count: 140, percentage: 20 },
      { grade: "C", count: 210, percentage: 30 },
      { grade: "D", count: 175, percentage: 25 },
      { grade: "F", count: 105, percentage: 15 },
    ],
  };
}

export function getMockMemberDetail(id: number): MemberDetail {
  const m = mockMembers.find((m) => m.id === id) ?? mockMembers[0];
  const score: ScoreDetail = {
    id: 1,
    member_id: m.id,
    session_id: 1,
    session_number: 213,
    legislative_activity_raw: 12.5,
    voting_behavior_raw: 88.0,
    policy_influence_raw: 5.2,
    transparency_raw: 45.0,
    legislative_activity: m.latest_score?.legislative_activity ?? 0,
    voting_behavior: m.latest_score?.voting_behavior ?? 0,
    policy_influence: m.latest_score?.policy_influence ?? 0,
    transparency: m.latest_score?.transparency ?? 0,
    total: m.latest_score?.total ?? 0,
    grade: m.latest_score?.grade ?? "F",
    breakdown: {
      legislative_activity: { bill_score: 4.5, committee_score: 8.0, speech_count: 15, avg_speech_chars: 4500 },
      voting_behavior: { votes_cast: 44, vote_opportunities: 50, participation_rate: 88.0 },
      policy_influence: { enacted_count: 2, enacted_score: 1.7 },
      transparency: { committee_speeches: 15, committee_meetings: 120, disclosure_rate: 12.5 },
    },
  };
  return { ...m, scores: [score] };
}

export function getMockBillDetail(): BillDetail {
  return {
    id: 1, session_id: 1, bill_kind: "閣法", bill_number: "1", title: "デジタル社会形成基本法の一部を改正する法律案", status: "成立", result: "成立", proposer_type: "cabinet", url: null,
    sponsors: [
      { member_id: 1, member_name: "山田太郎", sponsor_type: "primary" },
      { member_id: 3, member_name: "鈴木一郎", sponsor_type: "co-sponsor" },
    ],
    vote_results: [
      { id: 1, chamber: "representatives", ayes: 312, nays: 133, result: "可決" },
      { id: 2, chamber: "councillors", ayes: 168, nays: 77, result: "可決" },
    ],
  };
}
