const REVIEWER_ID_KEY = "giin-score-reviewer-id";
const DISPLAY_NAME_KEY = "giin-score-display-name";

export function getReviewerId(): string {
  if (typeof window === "undefined") return "";
  try {
    let id = localStorage.getItem(REVIEWER_ID_KEY);
    if (!id) {
      id = crypto.randomUUID();
      localStorage.setItem(REVIEWER_ID_KEY, id);
    }
    return id;
  } catch {
    return "";
  }
}

export function getDisplayName(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return localStorage.getItem(DISPLAY_NAME_KEY);
  } catch {
    return null;
  }
}

export function setDisplayName(name: string): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(DISPLAY_NAME_KEY, name);
  } catch {
    // ignore
  }
}
