import { Suspense } from "react";
import { LoadingSpinner } from "@/components/ui/loading";
import BillsContent from "./BillsContent";

export default function BillsPage() {
  return (
    <Suspense fallback={<div className="mx-auto max-w-7xl px-4 py-8"><LoadingSpinner /></div>}>
      <BillsContent />
    </Suspense>
  );
}
