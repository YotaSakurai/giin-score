"use client";

import { useState, useMemo } from "react";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { BillList } from "@/components/bill/BillList";
import type { Bill } from "@/lib/types";

const mockBills: Bill[] = [
  { id: 1, session_id: 1, bill_kind: "閣法", bill_number: "1", title: "デジタル社会形成基本法の一部を改正する法律案", status: "成立", result: "成立", proposer_type: "cabinet", url: null },
  { id: 2, session_id: 1, bill_kind: "衆法", bill_number: "5", title: "子ども・子育て支援法の一部を改正する法律案", status: "成立", result: "成立", proposer_type: "member", url: null },
  { id: 3, session_id: 1, bill_kind: "閣法", bill_number: "12", title: "地方自治法の一部を改正する法律案", status: "審議中", result: null, proposer_type: "cabinet", url: null },
  { id: 4, session_id: 1, bill_kind: "参法", bill_number: "3", title: "公職選挙法の一部を改正する法律案", status: "否決", result: "否決", proposer_type: "member", url: null },
  { id: 5, session_id: 1, bill_kind: "閣法", bill_number: "20", title: "防衛力整備計画に基づく財源確保に関する特別措置法案", status: "成立", result: "成立", proposer_type: "cabinet", url: null },
  { id: 6, session_id: 1, bill_kind: "衆法", bill_number: "8", title: "国民年金法等の一部を改正する法律案", status: "継続", result: null, proposer_type: "member", url: null },
  { id: 7, session_id: 1, bill_kind: "閣法", bill_number: "15", title: "出入国管理及び難民認定法の一部を改正する法律案", status: "成立", result: "成立", proposer_type: "cabinet", url: null },
  { id: 8, session_id: 1, bill_kind: "衆法", bill_number: "11", title: "再生可能エネルギー電気の利用の促進に関する特別措置法案", status: "廃案", result: "廃案", proposer_type: "member", url: null },
];

export default function BillsPage() {
  const [search, setSearch] = useState("");
  const [billKind, setBillKind] = useState("all");
  const [status, setStatus] = useState("all");

  const filtered = useMemo(() => {
    return mockBills.filter((b) => {
      if (search && !b.title.includes(search)) return false;
      if (billKind !== "all" && b.bill_kind !== billKind) return false;
      if (status !== "all" && b.status !== status) return false;
      return true;
    });
  }, [search, billKind, status]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <h1 className="text-2xl font-bold text-slate-800 mb-6">法案一覧</h1>

      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <Input
          placeholder="法案名で検索..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="sm:max-w-xs"
        />
        <Select value={billKind} onValueChange={setBillKind}>
          <SelectTrigger className="sm:w-40">
            <SelectValue placeholder="種別" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全種別</SelectItem>
            <SelectItem value="閣法">閣法</SelectItem>
            <SelectItem value="衆法">衆法</SelectItem>
            <SelectItem value="参法">参法</SelectItem>
          </SelectContent>
        </Select>
        <Select value={status} onValueChange={setStatus}>
          <SelectTrigger className="sm:w-40">
            <SelectValue placeholder="状態" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全状態</SelectItem>
            <SelectItem value="成立">成立</SelectItem>
            <SelectItem value="審議中">審議中</SelectItem>
            <SelectItem value="否決">否決</SelectItem>
            <SelectItem value="廃案">廃案</SelectItem>
            <SelectItem value="継続">継続</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <p className="text-sm text-slate-500 mb-4">{filtered.length}件の法案</p>
      <BillList bills={filtered} />
    </div>
  );
}
