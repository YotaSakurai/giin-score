"use client";

import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

interface MemberFilterProps {
  search: string;
  chamber: string;
  party: string;
  onSearchChange: (v: string) => void;
  onChamberChange: (v: string) => void;
  onPartyChange: (v: string) => void;
}

const PARTIES = [
  "自由民主党", "立憲民主党", "公明党", "日本維新の会",
  "国民民主党", "日本共産党", "れいわ新選組", "社会民主党", "無所属",
];

export function MemberFilter({ search, chamber, party, onSearchChange, onChamberChange, onPartyChange }: MemberFilterProps) {
  return (
    <div className="flex flex-col sm:flex-row gap-3 mb-6">
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
          {PARTIES.map((p) => (
            <SelectItem key={p} value={p}>{p}</SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
