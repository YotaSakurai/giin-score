import type { Metadata } from "next";
import { Suspense } from "react";
import { LoadingSpinner } from "@/components/ui/loading";
import HomeContent from "./HomeContent";

export const metadata: Metadata = {
  title: "議員活動ランキング | GiinScore",
  description:
    "国会議員の活動スコアランキング。立法活動・投票行動・政策影響力・透明性の4軸で議員のパフォーマンスを可視化します。",
  openGraph: {
    title: "議員活動ランキング | GiinScore",
    description:
      "国会議員の活動スコアランキング。立法活動・投票行動・政策影響力・透明性の4軸で議員のパフォーマンスを可視化します。",
  },
  twitter: {
    card: "summary_large_image",
    title: "議員活動ランキング | GiinScore",
    description:
      "国会議員の活動スコアランキング。立法活動・投票行動・政策影響力・透明性の4軸で議員のパフォーマンスを可視化します。",
  },
};

export default function HomePage() {
  return (
    <Suspense fallback={<div className="mx-auto max-w-7xl px-4 py-8"><LoadingSpinner /></div>}>
      <HomeContent />
    </Suspense>
  );
}
