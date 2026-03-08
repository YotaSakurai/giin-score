import { Suspense } from "react";
import { LoadingSpinner } from "@/components/ui/loading";
import CompareContent from "./CompareContent";

export default function ComparePage() {
  return (
    <Suspense fallback={<div className="mx-auto max-w-7xl px-4 py-8"><LoadingSpinner /></div>}>
      <CompareContent />
    </Suspense>
  );
}
