import type { MemberWithScore } from "@/lib/types";
import { MemberCard } from "./MemberCard";

interface MemberListProps {
  members: MemberWithScore[];
  onResetFilters?: () => void;
}

export function MemberList({ members, onResetFilters }: MemberListProps) {
  if (members.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <svg className="h-16 w-16 text-muted-foreground/40 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
        </svg>
        <p className="text-muted-foreground font-medium mb-1">該当する議員が見つかりません</p>
        <p className="text-sm text-muted-foreground/70 mb-4">検索条件や��ィルタを変更してお試しください</p>
        {onResetFilters && (
          <button
            type="button"
            onClick={onResetFilters}
            className="text-sm text-blue-600 hover:text-blue-700 font-medium"
          >
            フィルタをリセット
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 stagger-fade-in">
      {members.map((member) => (
        <MemberCard key={member.id} member={member} />
      ))}
    </div>
  );
}
