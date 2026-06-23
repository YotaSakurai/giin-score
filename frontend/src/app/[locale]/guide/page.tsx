import type { Metadata } from "next";
import { GuideContent } from "./GuideContent";

export const metadata: Metadata = {
  title: "使い方ガイド | GiinScore",
  description: "GiinScoreの各画面の操作方法を画像付きで説明します。ランキング・議員一覧・議員詳細・政党別統計・議員比較・質問品質ランキング・法案一覧の使い方。",
};

export default function GuidePage() {
  return <GuideContent />;
}
