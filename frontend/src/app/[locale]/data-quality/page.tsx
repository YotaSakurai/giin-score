import type { Metadata } from "next";
import { Suspense } from "react";
import { LoadingSpinner } from "@/components/ui/loading";
import DataQualityContent from "./DataQualityContent";

export const metadata: Metadata = {
  title: "データ品質",
  description: "会期ごとのデータ充足状況を確認できます。",
};

export default function DataQualityPage() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <DataQualityContent />
    </Suspense>
  );
}
