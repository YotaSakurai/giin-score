import { memo } from "react";
import { Link } from "@/i18n/navigation";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { Bill } from "@/lib/types";
import { STATUS_COLORS } from "@/lib/constants";

interface BillCardProps {
  bill: Bill;
  searchKeyword?: string;
}

function HighlightText({ text, keyword }: { text: string; keyword?: string }) {
  if (!keyword || keyword.length < 1) return <>{text}</>;
  const escaped = keyword.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const parts = text.split(new RegExp(`(${escaped})`, "gi"));
  return (
    <>
      {parts.map((part, i) =>
        part.toLowerCase() === keyword.toLowerCase() ? (
          <mark key={i} className="bg-yellow-200 dark:bg-yellow-800/60 text-inherit rounded-sm px-0.5">{part}</mark>
        ) : (
          part
        ),
      )}
    </>
  );
}

const KIND_COLORS: Record<string, string> = {
  閣法: "border-blue-500",
  衆法: "border-violet-500",
  参法: "border-amber-500",
};

export const BillCard = memo(function BillCard({ bill, searchKeyword }: BillCardProps) {
  const statusClass = STATUS_COLORS[bill.status ?? ""] ?? "bg-muted text-muted-foreground";
  const isEnacted = bill.status === "成立";
  const kindBorder = KIND_COLORS[bill.bill_kind] ?? "border-muted";

  return (
    <Link href={`/bills/${bill.id}`}>
      <Card className={`hover:shadow-md transition-shadow cursor-pointer border-l-4 ${kindBorder} ${isEnacted ? "ring-1 ring-emerald-200 dark:ring-emerald-800" : ""}`}>
        <CardContent className="p-4">
          <div className="flex items-start justify-between gap-2">
            <h3 className="font-medium text-foreground text-sm leading-tight flex-1">
              <HighlightText text={bill.title} keyword={searchKeyword} />
            </h3>
            {bill.status && (
              <Badge className={statusClass} variant="secondary">
                {bill.status}
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-2 mt-2 flex-wrap">
            <Badge variant="outline" className="text-xs">{bill.bill_kind}</Badge>
            {bill.bill_number && (
              <span className="text-xs text-muted-foreground">第{bill.bill_number}号</span>
            )}
            {bill.proposer_type && (
              <span className="text-xs text-muted-foreground">
                {bill.proposer_type === "cabinet" ? "内閣提出" : bill.proposer_type === "member" ? "議員提出" : bill.proposer_type}
              </span>
            )}
            {bill.result && bill.result !== bill.status && (
              <span className={`text-xs ${bill.result === "成立" ? "text-emerald-600 font-medium" : "text-muted-foreground"}`}>
                {bill.result}
              </span>
            )}
          </div>
        </CardContent>
      </Card>
    </Link>
  );
});
