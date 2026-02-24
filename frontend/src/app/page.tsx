import { Suspense } from "react";
import { LoadingSpinner } from "@/components/ui/loading";
import HomeContent from "./HomeContent";

export default function HomePage() {
  return (
    <Suspense fallback={<div className="mx-auto max-w-7xl px-4 py-8"><LoadingSpinner /></div>}>
      <HomeContent />
    </Suspense>
  );
}
