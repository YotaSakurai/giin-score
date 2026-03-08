import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "議員一覧",
  description: "国会議員の活動スコア一覧。院・政党でフィルタリングして議員を検索できます。",
};

export default function MembersLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
