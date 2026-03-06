"use client";

import { useCallback, useState } from "react";
import { getFavorites, toggleFavorite } from "@/lib/favorites";

interface FavoriteButtonProps {
  memberId: number;
  className?: string;
}

export function FavoriteButton({ memberId, className = "" }: FavoriteButtonProps) {
  const [isFav, setIsFav] = useState(() => getFavorites().includes(memberId));

  const handleClick = useCallback(() => {
    toggleFavorite(memberId);
    setIsFav((prev) => !prev);
  }, [memberId]);

  return (
    <button
      type="button"
      onClick={handleClick}
      className={`inline-flex items-center justify-center transition-colors ${className}`}
      aria-label={isFav ? "お気に入りから削除" : "お気に入りに追加"}
    >
      {isFav ? (
        <svg className="h-5 w-5 text-yellow-400" fill="currentColor" viewBox="0 0 24 24">
          <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
        </svg>
      ) : (
        <svg className="h-5 w-5 text-muted-foreground/50 hover:text-yellow-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
        </svg>
      )}
    </button>
  );
}
