import type { Metadata } from "next";
import { Suspense } from "react";
import { LoadingSpinner } from "@/components/ui/loading";
import QualityRankingContent from "./QualityRankingContent";

export const metadata: Metadata = {
  title: "質問品質ランキング | GiinScore",
  description: "国会議員の質問品質スコアランキング。建設的な政策議論ができている議員を可視化。",
  openGraph: {
    title: "質問品質ランキング | GiinScore",
    description: "国会議員の質問品質スコアランキング。建設的な政策議論ができている議員を可視化。",
  },
};

export default function QualityRankingPage() {
  return (
    <Suspense fallback={<div className="mx-auto max-w-7xl px-4 py-8"><LoadingSpinner /></div>}>
      <QualityRankingContent />
    </Suspense>
  );
}
