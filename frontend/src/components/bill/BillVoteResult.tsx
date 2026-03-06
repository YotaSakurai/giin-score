"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { CHAMBER_LABELS } from "@/lib/types";
import type { VoteResultSummary } from "@/lib/types";

interface BillVoteResultProps {
  voteResults: VoteResultSummary[];
}

const COLORS = { ayes: "#22c55e", nays: "#ef4444" };

export function BillVoteResult({ voteResults }: BillVoteResultProps) {
  if (voteResults.length === 0) {
    return null;
  }

  return (
    <div className="space-y-6">
      {voteResults.map((vr) => {
        const pieData = [
          { name: "賛成", value: vr.ayes },
          { name: "反対", value: vr.nays },
        ];

        return (
          <Card key={vr.id}>
            <CardHeader>
              <CardTitle className="text-base">
                {CHAMBER_LABELS[vr.chamber] ?? vr.chamber}
                {vr.result && <span className="ml-2 text-sm font-normal text-muted-foreground">({vr.result})</span>}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-col sm:flex-row items-center gap-6">
                <div className="w-48 h-48">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={70} label={({ name, value }) => `${name}: ${value}`}>
                        <Cell fill={COLORS.ayes} />
                        <Cell fill={COLORS.nays} />
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="flex-1 w-full h-32">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={[{ name: CHAMBER_LABELS[vr.chamber], 賛成: vr.ayes, 反対: vr.nays }]} layout="vertical">
                      <XAxis type="number" />
                      <YAxis type="category" dataKey="name" width={60} />
                      <Tooltip />
                      <Legend />
                      <Bar dataKey="賛成" fill={COLORS.ayes} />
                      <Bar dataKey="反対" fill={COLORS.nays} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
