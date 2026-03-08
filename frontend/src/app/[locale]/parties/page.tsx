import { Suspense } from "react";
import type { Metadata } from "next";
import { LoadingSpinner } from "@/components/ui/loading";
import PartyStatsContent from "./PartyStatsContent";

export const metadata: Metadata = {
  title: "政党別統計 | GiinScore",
  description: "政党別の議員活動スコア統計。各政党の平均スコア・中央値・各軸別の比較を確認できます。",
};

export default function PartyStatsPage() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <PartyStatsContent />
    </Suspense>
  );
}
