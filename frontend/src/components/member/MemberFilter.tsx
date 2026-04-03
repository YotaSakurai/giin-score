"use client";

import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useParties } from "@/lib/hooks";

interface MemberFilterProps {
  search: string;
  chamber: string;
  party: string;
  district?: string;
  onSearchChange: (v: string) => void;
  onChamberChange: (v: string) => void;
  onPartyChange: (v: string) => void;
  onDistrictChange?: (v: string) => void;
}

export function MemberFilter({
  search, chamber, party, district = "", onSearchChange, onChamberChange, onPartyChange, onDistrictChange,
}: MemberFilterProps) {
  const chamberParam = chamber === "all" ? undefined : chamber;
  const { data: parties } = useParties(chamberParam);

  return (
    <div className="flex flex-col sm:flex-row gap-3 mb-6 flex-wrap">
      <Input
        placeholder="議員名で検索..."
        value={search}
        onChange={(e) => onSearchChange(e.target.value)}
        className="sm:max-w-xs"
      />
      <Select value={chamber} onValueChange={onChamberChange}>
        <SelectTrigger className="sm:w-40">
          <SelectValue placeholder="院を選択" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">全て</SelectItem>
          <SelectItem value="representatives">衆議院</SelectItem>
          <SelectItem value="councillors">参議院</SelectItem>
        </SelectContent>
      </Select>
      <Select value={party} onValueChange={onPartyChange}>
        <SelectTrigger className="sm:w-48">
          <SelectValue placeholder="政党を選択" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">全政党</SelectItem>
          {(parties ?? []).map((p) => (
            <SelectItem key={p} value={p}>{p}</SelectItem>
          ))}
        </SelectContent>
      </Select>
      {onDistrictChange && (
        <Input
          placeholder="選挙区で検索..."
          value={district}
          onChange={(e) => onDistrictChange(e.target.value)}
          className="sm:max-w-[200px]"
        />
      )}
    </div>
  );
}
