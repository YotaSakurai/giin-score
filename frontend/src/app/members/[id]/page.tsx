import type { Metadata } from "next";
import { getMember } from "@/lib/api";
import MemberDetailContent from "./MemberDetailContent";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://giinscore.jp";

interface PageProps {
  params: Promise<{ id: string }>;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { id } = await params;
  try {
    const member = await getMember(Number(id));
    const latestScore = member.scores?.[0] ?? null;

    const title = `${member.name}のスコア`;
    const description = latestScore
      ? `${member.name}の国会活動スコア: 総合${latestScore.total.toFixed(1)}点（グレード${latestScore.grade}）`
      : `${member.name}の国会活動スコアを確認できます`;
    const url = `${siteUrl}/members/${id}`;

    return {
      title,
      description,
      openGraph: {
        type: "profile",
        title: `${title} | GiinScore`,
        description,
        url,
        siteName: "GiinScore",
        locale: "ja_JP",
      },
      twitter: {
        card: "summary_large_image",
        title: `${title} | GiinScore`,
        description,
      },
      alternates: {
        canonical: url,
      },
    };
  } catch {
    return {
      title: "議員詳細",
      description: "議員の国会活動スコアを確認できます",
    };
  }
}

export default function MemberDetailPage({ params }: PageProps) {
  return <MemberDetailContent params={params} />;
}
