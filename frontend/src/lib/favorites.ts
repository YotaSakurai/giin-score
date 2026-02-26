const FAVORITES_KEY = "giin-score-favorites";

export function getFavorites(): number[] {
  if (typeof window === "undefined") return [];
  try {
    const stored = localStorage.getItem(FAVORITES_KEY);
    if (!stored) return [];
    return JSON.parse(stored) as number[];
  } catch {
    return [];
  }
}

export function setFavorites(ids: number[]) {
  if (typeof window === "undefined") return;
  localStorage.setItem(FAVORITES_KEY, JSON.stringify(ids));
}

export function toggleFavorite(memberId: number): number[] {
  const current = getFavorites();
  const next = current.includes(memberId)
    ? current.filter((id) => id !== memberId)
    : [...current, memberId];
  setFavorites(next);
  return next;
}

export function isFavorite(memberId: number): boolean {
  return getFavorites().includes(memberId);
}
