import type { Metadata } from "next";
import { Suspense } from "react";
import { LoadingSpinner } from "@/components/ui/loading";
import CompareContent from "./CompareContent";

export const metadata: Metadata = {
  title: "議員比較 | GiinScore",
  description: "複数の国会議員のスコアをレーダーチャートで比較。立法活動・投票行動・政策影響力・透明性・質問品質の5軸で可視化。",
  openGraph: {
    title: "議員比較 | GiinScore",
    description: "複数の国会議員のスコアをレーダーチャートで比較",
  },
};

export default function ComparePage() {
  return (
    <Suspense fallback={<div className="mx-auto max-w-7xl px-4 py-8"><LoadingSpinner /></div>}>
      <CompareContent />
    </Suspense>
  );
}
