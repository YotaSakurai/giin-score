import type { MetadataRoute } from "next";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

async function fetchMemberIds(): Promise<number[]> {
  try {
    const res = await fetch(`${API_BASE}/members?per_page=100&page=1`, {
      next: { revalidate: 86400 },
    });
    if (!res.ok) return [];
    const data = await res.json();
    const pages = data.pages || 1;
    const ids: number[] = data.items.map((m: { id: number }) => m.id);

    // 残りのページも取得（最大10ページ = 1000人分）
    for (let p = 2; p <= Math.min(pages, 10); p++) {
      const pageRes = await fetch(`${API_BASE}/members?per_page=100&page=${p}`, {
        next: { revalidate: 86400 },
      });
      if (pageRes.ok) {
        const pageData = await pageRes.json();
        ids.push(...pageData.items.map((m: { id: number }) => m.id));
      }
    }
    return ids;
  } catch {
    return [];
  }
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://giinscore.jp";

  const staticPages: MetadataRoute.Sitemap = [
    {
      url: siteUrl,
      lastModified: new Date(),
      changeFrequency: "daily",
      priority: 1,
    },
    {
      url: `${siteUrl}/members`,
      lastModified: new Date(),
      changeFrequency: "daily",
      priority: 0.9,
    },
    {
      url: `${siteUrl}/parties`,
      lastModified: new Date(),
      changeFrequency: "daily",
      priority: 0.8,
    },
    {
      url: `${siteUrl}/compare`,
      lastModified: new Date(),
      changeFrequency: "weekly",
      priority: 0.7,
    },
    {
      url: `${siteUrl}/bills`,
      lastModified: new Date(),
      changeFrequency: "daily",
      priority: 0.8,
    },
    {
      url: `${siteUrl}/favorites`,
      lastModified: new Date(),
      changeFrequency: "weekly",
      priority: 0.5,
    },
    {
      url: `${siteUrl}/about`,
      lastModified: new Date(),
      changeFrequency: "monthly",
      priority: 0.5,
    },
  ];

  // 動的な議員個別ページ
  const memberIds = await fetchMemberIds();
  const memberPages: MetadataRoute.Sitemap = memberIds.map((id) => ({
    url: `${siteUrl}/members/${id}`,
    lastModified: new Date(),
    changeFrequency: "weekly" as const,
    priority: 0.6,
  }));

  return [...staticPages, ...memberPages];
}
