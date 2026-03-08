import { Suspense } from "react";
import type { Metadata } from "next";
import { LoadingSpinner } from "@/components/ui/loading";
import FavoritesContent from "./FavoritesContent";

export const metadata: Metadata = {
  title: "お気に入り | GiinScore",
  description: "お気に入り登録した議員の活動スコアを一覧で確認できます。",
};

export default function FavoritesPage() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <FavoritesContent />
    </Suspense>
  );
}
