// docs/capture-screenshots.mjs
// 各画面のスクリーンショットを撮影するスクリプト
import { chromium } from "playwright-core";
import { join as joinCachePath } from "path";

// Playwright browsers installed via npx playwright install
process.env.PLAYWRIGHT_BROWSERS_PATH = joinCachePath(process.env.HOME || "", ".cache", "ms-playwright");
import { mkdirSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const imgDir = join(__dirname, "images");
mkdirSync(imgDir, { recursive: true });

const BASE = "http://localhost:3000/ja";

const pages = [
  // デスクトップ版
  { name: "home-desktop", path: "/", viewport: { width: 1440, height: 900 }, waitFor: 3000 },
  { name: "home-desktop-stats", path: "/", viewport: { width: 1440, height: 900 }, waitFor: 3000, scrollTo: 200 },
  { name: "members-desktop", path: "/members", viewport: { width: 1440, height: 900 }, waitFor: 3000 },
  { name: "members-table", path: "/members?view=table", viewport: { width: 1440, height: 900 }, waitFor: 3000 },
  { name: "members-scatter", path: "/members?view=scatter", viewport: { width: 1440, height: 900 }, waitFor: 4000 },
  { name: "parties-desktop", path: "/parties", viewport: { width: 1440, height: 900 }, waitFor: 3000 },
  { name: "compare-desktop", path: "/compare", viewport: { width: 1440, height: 900 }, waitFor: 3000 },
  { name: "quality-ranking", path: "/quality-ranking", viewport: { width: 1440, height: 900 }, waitFor: 3000 },
  { name: "bills-desktop", path: "/bills", viewport: { width: 1440, height: 900 }, waitFor: 3000 },
  { name: "favorites-desktop", path: "/favorites", viewport: { width: 1440, height: 900 }, waitFor: 2000 },
  { name: "about-desktop", path: "/about", viewport: { width: 1440, height: 900 }, waitFor: 2000 },
  { name: "data-quality", path: "/data-quality", viewport: { width: 1440, height: 900 }, waitFor: 3000 },
  { name: "api-docs", path: "/api-docs", viewport: { width: 1440, height: 900 }, waitFor: 2000 },

  // モバイル版 (主要ページのみ)
  { name: "home-mobile", path: "/", viewport: { width: 390, height: 844 }, waitFor: 3000 },
  { name: "members-mobile", path: "/members", viewport: { width: 390, height: 844 }, waitFor: 3000 },
  { name: "bills-mobile", path: "/bills", viewport: { width: 390, height: 844 }, waitFor: 3000 },

  // ダークモード
  { name: "home-dark", path: "/", viewport: { width: 1440, height: 900 }, waitFor: 3000, dark: true },
  { name: "members-dark", path: "/members", viewport: { width: 1440, height: 900 }, waitFor: 3000, dark: true },
];

async function main() {
  const browser = await chromium.launch({ headless: true });

  for (const pg of pages) {
    console.log(`Capturing: ${pg.name} ...`);
    const context = await browser.newContext({
      viewport: pg.viewport,
      colorScheme: pg.dark ? "dark" : "light",
    });
    const page = await context.newPage();

    // ダークモード設定
    if (pg.dark) {
      await page.addInitScript(() => {
        localStorage.setItem("theme", "dark");
      });
    }

    try {
      await page.goto(`${BASE}${pg.path}`, { waitUntil: "networkidle", timeout: 15000 });
    } catch {
      // networkidle timeout is ok, just wait for content
      await page.waitForTimeout(2000);
    }
    await page.waitForTimeout(pg.waitFor);

    // ダークモードのクラス適用を確認
    if (pg.dark) {
      await page.evaluate(() => {
        document.documentElement.classList.add("dark");
      });
      await page.waitForTimeout(500);
    }

    if (pg.scrollTo) {
      await page.evaluate((y) => window.scrollTo(0, y), pg.scrollTo);
      await page.waitForTimeout(500);
    }

    await page.screenshot({
      path: join(imgDir, `${pg.name}.png`),
      fullPage: false,
    });
    await context.close();
  }

  // 議員詳細ページ - 実在する議員IDを取得
  console.log("Capturing: member-detail ...");
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const detailPage = await ctx.newPage();
  try {
    // まずランキングから最初の議員IDを取得
    const resp = await detailPage.goto(`${BASE}/`, { waitUntil: "networkidle", timeout: 15000 });
    await detailPage.waitForTimeout(3000);
  } catch {}

  // 議員リンクから最初の議員を取得
  const memberLink = await detailPage.$('a[href*="/members/"]');
  if (memberLink) {
    const href = await memberLink.getAttribute("href");
    const memberId = href?.match(/\/members\/(\d+)/)?.[1];
    if (memberId) {
      try {
        await detailPage.goto(`${BASE}/members/${memberId}`, { waitUntil: "networkidle", timeout: 15000 });
      } catch {}
      await detailPage.waitForTimeout(3000);
      await detailPage.screenshot({
        path: join(imgDir, "member-detail-desktop.png"),
        fullPage: false,
      });

      // スコアタブ部分もスクロール
      await detailPage.evaluate(() => window.scrollTo(0, 500));
      await detailPage.waitForTimeout(500);
      await detailPage.screenshot({
        path: join(imgDir, "member-detail-scores.png"),
        fullPage: false,
      });
    }
  }
  await ctx.close();

  // 法案詳細ページ
  console.log("Capturing: bill-detail ...");
  const bCtx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const billPage = await bCtx.newPage();
  try {
    await billPage.goto(`${BASE}/bills`, { waitUntil: "networkidle", timeout: 15000 });
    await billPage.waitForTimeout(3000);
  } catch {}
  const billLink = await billPage.$('a[href*="/bills/"]');
  if (billLink) {
    const href = await billLink.getAttribute("href");
    const billId = href?.match(/\/bills\/(\d+)/)?.[1];
    if (billId) {
      try {
        await billPage.goto(`${BASE}/bills/${billId}`, { waitUntil: "networkidle", timeout: 15000 });
      } catch {}
      await billPage.waitForTimeout(3000);
      await billPage.screenshot({
        path: join(imgDir, "bill-detail-desktop.png"),
        fullPage: false,
      });
    }
  }
  await bCtx.close();

  await browser.close();
  console.log("Done! Screenshots saved to docs/images/");
}

main().catch(console.error);
