"use client";

import { useState, useMemo } from "react";
import { MemberList } from "@/components/member/MemberList";
import { MemberFilter } from "@/components/member/MemberFilter";
import { getMockMembers } from "@/lib/mock-data";

export default function MembersPage() {
  const [search, setSearch] = useState("");
  const [chamber, setChamber] = useState("all");
  const [party, setParty] = useState("all");

  const allMembers = getMockMembers();

  const filtered = useMemo(() => {
    return allMembers.filter((m) => {
      if (search && !m.name.includes(search) && !m.name_reading?.includes(search)) return false;
      if (chamber !== "all" && m.chamber !== chamber) return false;
      if (party !== "all" && m.party !== party) return false;
      return true;
    });
  }, [allMembers, search, chamber, party]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <h1 className="text-2xl font-bold text-slate-800 mb-6">議員一覧</h1>
      <MemberFilter
        search={search}
        chamber={chamber}
        party={party}
        onSearchChange={setSearch}
        onChamberChange={setChamber}
        onPartyChange={setParty}
      />
      <p className="text-sm text-slate-500 mb-4">{filtered.length}名の議員</p>
      <MemberList members={filtered} />
    </div>
  );
}
