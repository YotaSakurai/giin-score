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
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ja" suppressHydrationWarning>
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
