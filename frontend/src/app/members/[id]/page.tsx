import type { Metadata } from "next";
import { getMember } from "@/lib/api";
import MemberDetailContent from "./MemberDetailContent";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://giinscore.jp";
const CHAMBER_LABELS: Record<string, string> = {
  representatives: "衆議院",
  councillors: "参議院",
};

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

export default async function MemberDetailPage({ params }: PageProps) {
  const { id } = await params;
  let jsonLd = null;

  try {
    const member = await getMember(Number(id));
    const latestScore = member.scores?.[0] ?? null;

    jsonLd = {
      "@context": "https://schema.org",
      "@type": "Person",
      name: member.name,
      url: `${siteUrl}/members/${id}`,
      description: latestScore
        ? `${member.name}（${member.party ?? "無所属"}・${CHAMBER_LABELS[member.chamber] ?? member.chamber}）の国会活動スコア: ${latestScore.total.toFixed(1)}点`
        : `${member.name}の国会活動スコア`,
      affiliation: member.party
        ? {
            "@type": "Organization",
            name: member.party,
          }
        : undefined,
      memberOf: {
        "@type": "Organization",
        name: CHAMBER_LABELS[member.chamber] ?? member.chamber,
      },
    };
  } catch {
    // JSON-LDなしで表示
  }

  return (
    <>
      {jsonLd && (
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      )}
      <MemberDetailContent params={params} />
    </>
  );
}
