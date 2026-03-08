import { Suspense } from "react";
import { LoadingSpinner } from "@/components/ui/loading";
import MembersContent from "./MembersContent";

export default function MembersPage() {
  return (
    <Suspense fallback={<div className="mx-auto max-w-7xl px-4 py-8"><LoadingSpinner /></div>}>
      <MembersContent />
    </Suspense>
  );
}
