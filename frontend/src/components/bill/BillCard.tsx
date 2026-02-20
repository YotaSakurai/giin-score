import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { Bill } from "@/lib/types";

interface BillCardProps {
  bill: Bill;
}

const statusColors: Record<string, string> = {
  成立: "bg-emerald-100 text-emerald-800",
  否決: "bg-red-100 text-red-800",
  審議中: "bg-yellow-100 text-yellow-800",
  廃案: "bg-slate-100 text-slate-600",
  継続: "bg-blue-100 text-blue-800",
};

export function BillCard({ bill }: BillCardProps) {
  const statusClass = statusColors[bill.status ?? ""] ?? "bg-slate-100 text-slate-600";

  return (
    <Link href={`/bills/${bill.id}`}>
      <Card className="hover:shadow-md transition-shadow cursor-pointer">
        <CardContent className="p-4">
          <div className="flex items-start justify-between gap-2">
            <h3 className="font-medium text-slate-800 text-sm leading-tight flex-1">
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
              <span className="text-xs text-slate-500">第{bill.bill_number}号</span>
            )}
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
