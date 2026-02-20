import type { MemberWithScore } from "@/lib/types";
import { MemberCard } from "./MemberCard";

interface MemberListProps {
  members: MemberWithScore[];
}

export function MemberList({ members }: MemberListProps) {
  if (members.length === 0) {
    return (
      <div className="text-center py-12 text-slate-500">
        該当する議員が見つかりません
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      {members.map((member) => (
        <MemberCard key={member.id} member={member} />
      ))}
    </div>
  );
}
