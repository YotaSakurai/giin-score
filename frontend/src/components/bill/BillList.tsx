import type { Bill } from "@/lib/types";
import { BillCard } from "./BillCard";

interface BillListProps {
  bills: Bill[];
  searchKeyword?: string;
}

export function BillList({ bills, searchKeyword }: BillListProps) {
  if (bills.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        該当する法案が見つかりません
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {bills.map((bill) => (
        <BillCard key={bill.id} bill={bill} searchKeyword={searchKeyword} />
      ))}
    </div>
  );
}
