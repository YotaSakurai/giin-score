import type { Metadata } from "next";
import { Suspense } from "react";
import { LoadingSpinner } from "@/components/ui/loading";
import HomeContent from "./HomeContent";

export const metadata: Metadata = {
  title: "議員活動ランキング | GiinScore",
  description:
    "国会議員の活動スコアランキング。立法活動・投票行動・政策影響力・透明性の4軸で議員のパフォーマンスを可視化します。",
  openGraph: {
    title: "議員活動ランキング | GiinScore",
    description:
      "国会議員の活動スコアランキング。立法活動・投票行動・政策影響力・透明性の4軸で議員のパフォーマンスを可視化します。",
  },
  twitter: {
    card: "summary_large_image",
    title: "議員活動ランキング | GiinScore",
    description:
      "国会議員の活動スコアランキング。立法活動・投票行動・政策影響力・透明性の4軸で議員のパフォーマンスを可視化します。",
  },
};

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://giinscore.jp";

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "WebApplication",
  name: "GiinScore",
  url: siteUrl,
  description: "国会の公開データに基づく政治家の活動量を可視化するダッシュボード",
  applicationCategory: "GovernmentApplication",
  operatingSystem: "Web",
  inLanguage: "ja",
};

export default function HomePage() {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <Suspense fallback={<div className="mx-auto max-w-7xl px-4 py-8"><LoadingSpinner /></div>}>
        <HomeContent />
      </Suspense>
    </>
  );
}
