import type { Metadata } from "next";
import { getBill } from "@/lib/api";
import BillDetailContent from "./BillDetailContent";

interface PageProps {
  params: Promise<{ id: string }>;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { id } = await params;
  try {
    const bill = await getBill(Number(id));
    const title = `${bill.title} | GiinScore`;
    const description = `${bill.bill_kind}${bill.bill_number ? ` 第${bill.bill_number}号` : ""} - ${bill.status ?? "審議中"}`;

    return {
      title,
      description,
      openGraph: {
        title,
        description,
      },
    };
  } catch {
    return {
      title: "法案詳細 | GiinScore",
      description: "法案の詳細情報と投票結果を確認できます",
    };
  }
}

export default function BillDetailPage({ params }: PageProps) {
  return <BillDetailContent params={params} />;
}
