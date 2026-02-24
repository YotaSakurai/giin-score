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
