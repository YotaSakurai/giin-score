import type { Bill } from "@/lib/types";
import { BillCard } from "./BillCard";

interface BillListProps {
  bills: Bill[];
}

export function BillList({ bills }: BillListProps) {
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
        <BillCard key={bill.id} bill={bill} />
      ))}
    </div>
  );
}
