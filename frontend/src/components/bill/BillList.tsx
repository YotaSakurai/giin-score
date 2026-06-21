import type { Bill } from "@/lib/types";
import { BillCard } from "./BillCard";

interface BillListProps {
  bills: Bill[];
  searchKeyword?: string;
}

export function BillList({ bills, searchKeyword }: BillListProps) {
  if (bills.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <svg className="h-16 w-16 text-muted-foreground/40 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        <p className="text-muted-foreground font-medium mb-1">該当する法案が見つかりません</p>
        <p className="text-sm text-muted-foreground/70">検索条件を変更してお試しください</p>
      </div>
    );
  }

  return (
    <div className="space-y-3 stagger-fade-in">
      {bills.map((bill) => (
        <BillCard key={bill.id} bill={bill} searchKeyword={searchKeyword} />
      ))}
    </div>
  );
}
