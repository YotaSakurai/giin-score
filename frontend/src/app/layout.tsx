import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "@/components/ThemeProvider";
import { SWRProvider } from "@/components/SWRProvider";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const siteName = "GiinScore";
const siteDescription =
  "国会の公開データに基づく政治家の活動量を可視化するダッシュボード。立法活動・投票行動・政策影響力・透明性の4軸で議員のパフォーマンスを定量化します。";
const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://giinscore.jp";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: `${siteName} - 政治家活動スコアリングダッシュボード`,
    template: `%s | ${siteName}`,
  },
  description: siteDescription,
  keywords: ["議員", "国会", "スコア", "ランキング", "投票記録", "質問品質", "政党", "立法活動", "GiinScore"],
  openGraph: {
    type: "website",
    siteName,
    title: `${siteName} - 政治家活動スコアリングダッシュボード`,
    description: siteDescription,
    url: siteUrl,
    locale: "ja_JP",
  },
  twitter: {
    card: "summary_large_image",
    title: `${siteName} - 政治家活動スコアリングダッシュボード`,
    description: siteDescription,
  },
  alternates: {
    canonical: siteUrl,
  },
  other: {
    "apple-mobile-web-app-capable": "yes",
    "apple-mobile-web-app-status-bar-style": "default",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ja" suppressHydrationWarning>
      <head>
        <meta name="theme-color" content="#2563eb" media="(prefers-color-scheme: light)" />
        <meta name="theme-color" content="#1e293b" media="(prefers-color-scheme: dark)" />
      </head>
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased min-h-screen flex flex-col`}>
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
          <SWRProvider>
            {children}
          </SWRProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
