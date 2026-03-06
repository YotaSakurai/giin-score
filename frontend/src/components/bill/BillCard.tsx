import { memo } from "react";
import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { Bill } from "@/lib/types";
import { STATUS_COLORS } from "@/lib/constants";

interface BillCardProps {
  bill: Bill;
}

export const BillCard = memo(function BillCard({ bill }: BillCardProps) {
  const statusClass = STATUS_COLORS[bill.status ?? ""] ?? "bg-muted text-muted-foreground";

  return (
    <Link href={`/bills/${bill.id}`}>
      <Card className="hover:shadow-md transition-shadow cursor-pointer">
        <CardContent className="p-4">
          <div className="flex items-start justify-between gap-2">
            <h3 className="font-medium text-foreground text-sm leading-tight flex-1">
              {bill.title}
            </h3>
            {bill.status && (
              <Badge className={statusClass} variant="secondary">
                {bill.status}
              </Badge>
            )}
          </div>
          <div className="flex gap-2 mt-2">
            <Badge variant="outline" className="text-xs">{bill.bill_kind}</Badge>
            {bill.bill_number && (
              <span className="text-xs text-muted-foreground">第{bill.bill_number}号</span>
            )}
          </div>
        </CardContent>
      </Card>
    </Link>
  );
});
