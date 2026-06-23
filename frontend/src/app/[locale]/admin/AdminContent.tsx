"use client";

import { useState, useCallback } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import useSWR from "swr";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { LoadingSpinner } from "@/components/ui/loading";
import { ErrorMessage } from "@/components/ui/error";
import { SleepingReviewCard } from "@/components/admin/SleepingReviewCard";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

interface SleepingDetection {
  id: number;
  member_id: number | null;
  member_name: string | null;
  session_id: number;
  session_number: number | null;
  video_url: string;
  video_date: string | null;
  meeting_name: string | null;
  start_time_sec: number;
  end_time_sec: number;
  duration_sec: number;
  detection_type: string;
  confidence: number;
  head_angle_avg: number | null;
  screenshot_path: string | null;
  clip_path: string | null;
  identified_by: string | null;
  review_status: string;
  reviewed_at: string | null;
  review_note: string | null;
  detected_at: string;
}

interface SleepingStats {
  total_detections: number;
  pending: number;
  approved: number;
  rejected: number;
  members_with_incidents: number;
}

function adminFetcher(token: string) {
  return async (path: string) => {
    const res = await fetch(`${API_BASE}${path}`, {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    });
    if (res.status === 401) throw new Error("UNAUTHORIZED");
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  };
}

export default function AdminContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [token, setToken] = useState(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("admin_token") || "";
    }
    return "";
  });
  const [tokenInput, setTokenInput] = useState("");
  const [isAuthenticated, setIsAuthenticated] = useState(() => !!token);
  const [loginError, setLoginError] = useState("");

  const statusFilter = searchParams.get("status") || "pending";

  const updateParams = useCallback(
    (updates: Record<string, string | undefined>) => {
      const params = new URLSearchParams(searchParams.toString());
      Object.entries(updates).forEach(([key, value]) => {
        if (value === undefined || value === "" || value === "all") {
          params.delete(key);
        } else {
          params.set(key, value);
        }
      });
      const qs = params.toString();
      router.push(qs ? `?${qs}` : "");
    },
    [router, searchParams],
  );

  const handleLogin = async () => {
    setLoginError("");
    try {
      const res = await fetch(`${API_BASE}/sleeping/auth/verify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: tokenInput }),
      });
      const data = await res.json();
      if (data.valid) {
        setToken(tokenInput);
        setIsAuthenticated(true);
        localStorage.setItem("admin_token", tokenInput);
      } else {
        setLoginError("無効なトークンです");
      }
    } catch {
      setLoginError("認証サーバーに接続できません");
    }
  };

  const handleLogout = () => {
    setToken("");
    setTokenInput("");
    setIsAuthenticated(false);
    localStorage.removeItem("admin_token");
  };

  if (!isAuthenticated) {
    return (
      <div className="mx-auto max-w-md px-4 py-20">
        <Card>
          <CardHeader>
            <CardTitle className="text-center">管理画面ログイン</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <Input
              type="password"
              placeholder="管理者トークンを入力"
              value={tokenInput}
              onChange={(e) => setTokenInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleLogin()}
            />
            {loginError && (
              <p className="text-sm text-red-600 dark:text-red-400">
                {loginError}
              </p>
            )}
            <Button className="w-full" onClick={handleLogin}>
              ログイン
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">居眠り検出 管理画面</h1>
        <Button variant="outline" size="sm" onClick={handleLogout}>
          ログアウト
        </Button>
      </div>

      <StatsSection token={token} />

      <div className="flex items-center gap-3">
        <span className="text-sm font-medium text-muted-foreground">
          ステータス:
        </span>
        <Select
          value={statusFilter}
          onValueChange={(v) => updateParams({ status: v })}
        >
          <SelectTrigger className="w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="pending">未レビュー</SelectItem>
            <SelectItem value="approved">承認済み</SelectItem>
            <SelectItem value="rejected">却下済み</SelectItem>
            <SelectItem value="all">すべて</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <DetectionsList
        token={token}
        statusFilter={statusFilter === "all" ? undefined : statusFilter}
        onAuthError={handleLogout}
      />
    </div>
  );
}

function StatsSection({ token }: { token: string }) {
  const { data, error } = useSWR<SleepingStats>(
    "/sleeping/stats",
    adminFetcher(token),
  );

  if (error) return null;
  if (!data) return null;

  return (
    <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
      <StatCard label="総検出数" value={data.total_detections} />
      <StatCard
        label="未レビュー"
        value={data.pending}
        variant={data.pending > 0 ? "warning" : "default"}
      />
      <StatCard label="承認済み" value={data.approved} variant="success" />
      <StatCard label="却下済み" value={data.rejected} variant="muted" />
      <StatCard label="該当議員数" value={data.members_with_incidents} />
    </div>
  );
}

function StatCard({
  label,
  value,
  variant = "default",
}: {
  label: string;
  value: number;
  variant?: "default" | "warning" | "success" | "muted";
}) {
  const colors = {
    default: "text-foreground",
    warning: "text-amber-600 dark:text-amber-400",
    success: "text-emerald-600 dark:text-emerald-400",
    muted: "text-muted-foreground",
  };
  return (
    <Card>
      <CardContent className="pt-4 pb-3 text-center">
        <p className="text-xs text-muted-foreground mb-1">{label}</p>
        <p className={`text-2xl font-bold ${colors[variant]}`}>{value}</p>
      </CardContent>
    </Card>
  );
}

function DetectionsList({
  token,
  statusFilter,
  onAuthError,
}: {
  token: string;
  statusFilter?: string;
  onAuthError: () => void;
}) {
  const queryParams = statusFilter ? `?status=${statusFilter}` : "";
  const {
    data,
    error,
    isLoading,
    mutate,
  } = useSWR<{ total: number; items: SleepingDetection[] }>(
    `/sleeping/detections${queryParams}`,
    adminFetcher(token),
  );

  const handleReview = async (
    id: number,
    status: string,
    note?: string,
    memberId?: number,
  ) => {
    const body: Record<string, unknown> = { status };
    if (note) body.note = note;
    if (memberId) body.member_id = memberId;

    const res = await fetch(`${API_BASE}/sleeping/detections/${id}/review`, {
      method: "PUT",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });
    if (res.status === 401) {
      onAuthError();
      return;
    }
    if (!res.ok) throw new Error("Review failed");
    mutate();
  };

  if (isLoading) return <LoadingSpinner />;
  if (error) {
    if (error.message === "UNAUTHORIZED") {
      onAuthError();
      return null;
    }
    return <ErrorMessage message="データの取得に失敗しました" onRetry={() => mutate()} />;
  }
  if (!data || data.items.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-muted-foreground">
          該当する検出結果はありません
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        {data.total}件の検出結果
      </p>
      {data.items.map((det) => (
        <SleepingReviewCard
          key={det.id}
          detection={det}
          onReview={handleReview}
        />
      ))}
    </div>
  );
}
