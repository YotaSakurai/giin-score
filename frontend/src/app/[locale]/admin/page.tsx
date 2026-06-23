import type { Metadata } from "next";
import { Suspense } from "react";
import { LoadingSpinner } from "@/components/ui/loading";
import AdminContent from "./AdminContent";

export const metadata: Metadata = {
  title: "管理画面 | GiinScore",
  description: "居眠り検出レビュー管理画面",
  robots: { index: false, follow: false },
};

export default function AdminPage() {
  return (
    <Suspense
      fallback={
        <div className="mx-auto max-w-7xl px-4 py-8">
          <LoadingSpinner />
        </div>
      }
    >
      <AdminContent />
    </Suspense>
  );
}
