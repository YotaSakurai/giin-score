/** 法案ステータスに対応するBadge用カラークラス */
export const STATUS_COLORS: Record<string, string> = {
  成立: "bg-emerald-100 text-emerald-800",
  否決: "bg-red-100 text-red-800",
  審議中: "bg-yellow-100 text-yellow-800",
  廃案: "bg-red-100 text-red-800",
  継続: "bg-blue-100 text-blue-800",
};

/** 投票ラベル */
export const VOTE_LABELS: Record<string, string> = {
  aye: "賛成",
  nay: "反対",
  abstain: "棄権",
  absent: "欠席",
};

/** 投票Badgeカラー */
export const VOTE_COLORS: Record<string, string> = {
  aye: "bg-emerald-100 text-emerald-800",
  nay: "bg-red-100 text-red-800",
  abstain: "bg-yellow-100 text-yellow-800",
  absent: "bg-slate-100 text-slate-600",
};

/** スコア各軸の解説（初心者向け） */
export const SCORE_DESCRIPTIONS: Record<string, { short: string; detail: string }> = {
  legislative_activity: {
    short: "法案提出・委員会質疑・質問主意書など、立法に関する活動量",
    detail: "法案の発議（主提案か共同提案か、共同提案者数も考慮）、委員会での質疑回数・発言量、質問主意書の提出数を総合的に評価します。活発に法案を出し、委員会で質疑を行っている議員ほど高スコアになります。",
  },
  voting_behavior: {
    short: "本会議・委員会の採決にどれだけ参加しているか",
    detail: "投票機会に対する実際の投票参加率を評価します。欠席が多い議員は低スコアになります。棄権は参加とみなしますが、無断欠席は非参加として減点されます。",
  },
  policy_influence: {
    short: "提出した法案がどれだけ成立したか、質問主意書への回答状況",
    detail: "成立した法案の数と種類（閣法・議員立法など法案の重要度で重み付け）、答弁付き質問主意書の数から、実際に政策に影響を与えた度合いを評価します。法案を出すだけでなく、成立させる力がある議員が高スコアになります。",
  },
  transparency: {
    short: "多様な委員会に参加しているか（活動の幅広さ）",
    detail: "所属する委員会以外にも多様な委員会に出席し、幅広い政策分野に関わっているかを評価します。特定の委員会だけでなく、多くの分野で活動する議員が高スコアになります。",
  },
  question_quality: {
    short: "国会での質問が建設的で政策的に意味のある内容か",
    detail: "AI分析により、各発言の政策関連性・建設性・専門性・国益への貢献度を4軸で評価しています。スキャンダル追及や確認質問だけでなく、具体的な政策提案を伴う質問が高評価となります。",
  },
  total: {
    short: "5つの指標を重み付けして算出した総合評価",
    detail: "立法活動(25%)・投票行動(20%)・政策影響力(20%)・透明性(15%)・質問品質(20%)を加重平均した総合スコアです。同じ院・同じ役職カテゴリの議員同士でパーセンタイルランクに変換しています。",
  },
};

/** グレードの解説 */
export const GRADE_DESCRIPTIONS: Record<string, string> = {
  A: "上位20% — 非常に活発な議会活動を行っている議員",
  B: "上位40% — 平均以上の議会活動を行っている議員",
  C: "中位 — 平均的な議会活動レベルの議員",
  D: "下位40% — 議会活動が平均を下回る議員",
  F: "下位20% — 議会活動が非常に少ない議員",
};
