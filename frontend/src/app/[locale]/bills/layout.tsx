import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "法案一覧",
  description: "国会に提出された法案の一覧。種別・状態でフィルタリングして法案を検索できます。",
};

export default function BillsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
