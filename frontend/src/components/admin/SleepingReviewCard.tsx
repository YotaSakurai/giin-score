"use client";

import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  CheckCircle2,
  XCircle,
  Clock,
  ArrowDown,
  ArrowUp,
  ExternalLink,
} from "lucide-react";

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

interface Props {
  detection: SleepingDetection;
  onReview: (
    id: number,
    status: string,
    note?: string,
    memberId?: number,
  ) => Promise<void>;
}

const STATUS_CONFIG = {
  pending: {
    label: "未レビュー",
    color:
      "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300",
    icon: Clock,
  },
  approved: {
    label: "承認済み",
    color:
      "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300",
    icon: CheckCircle2,
  },
  rejected: {
    label: "却下済み",
    color:
      "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400",
    icon: XCircle,
  },
} as const;

function formatTime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) return `${h}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function formatDuration(seconds: number): string {
  if (seconds >= 60) {
    const m = Math.floor(seconds / 60);
    const s = Math.round(seconds % 60);
    return s > 0 ? `${m}分${s}秒` : `${m}分`;
  }
  return `${Math.round(seconds)}秒`;
}

export function SleepingReviewCard({ detection: det, onReview }: Props) {
  const [note, setNote] = useState(det.review_note || "");
  const [memberIdInput, setMemberIdInput] = useState(
    det.member_id?.toString() || "",
  );
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [expanded, setExpanded] = useState(det.review_status === "pending");

  const status = STATUS_CONFIG[det.review_status as keyof typeof STATUS_CONFIG] || STATUS_CONFIG.pending;
  const StatusIcon = status.icon;

  const handleSubmit = async (reviewStatus: string) => {
    setIsSubmitting(true);
    try {
      await onReview(
        det.id,
        reviewStatus,
        note || undefined,
        memberIdInput ? Number(memberIdInput) : undefined,
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Card
      className={
        det.review_status === "pending"
          ? "border-amber-300 dark:border-amber-700"
          : ""
      }
    >
      <CardContent className="pt-4 pb-4 space-y-3">
        {/* ヘッダー行 */}
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2 flex-wrap">
            <Badge className={status.color}>
              <StatusIcon className="h-3 w-3 mr-1" />
              {status.label}
            </Badge>

            <Badge variant="outline">
              {det.detection_type === "head_forward" ? (
                <>
                  <ArrowDown className="h-3 w-3 mr-1" />
                  前傾（うつむき）
                </>
              ) : (
                <>
                  <ArrowUp className="h-3 w-3 mr-1" />
                  後傾（仰向け）
                </>
              )}
            </Badge>

            <Badge variant="secondary">
              信頼度: {(det.confidence * 100).toFixed(0)}%
            </Badge>

            {det.head_angle_avg && (
              <Badge variant="secondary">
                角度: {det.head_angle_avg.toFixed(1)}°
              </Badge>
            )}
          </div>

          <Button
            variant="ghost"
            size="sm"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? "閉じる" : "詳細"}
          </Button>
        </div>

        {/* 基本情報 */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-x-4 gap-y-1 text-sm">
          <div>
            <span className="text-muted-foreground">議員:</span>{" "}
            <span className="font-medium">
              {det.member_name || "未特定"}
            </span>
          </div>
          <div>
            <span className="text-muted-foreground">会議:</span>{" "}
            {det.meeting_name || "不明"}
          </div>
          <div>
            <span className="text-muted-foreground">時刻:</span>{" "}
            {formatTime(det.start_time_sec)} - {formatTime(det.end_time_sec)}
          </div>
          <div>
            <span className="text-muted-foreground">持続:</span>{" "}
            <span className="font-medium text-red-600 dark:text-red-400">
              {formatDuration(det.duration_sec)}
            </span>
          </div>
        </div>

        {/* 動画リンク */}
        {det.video_url && (
          <div className="flex items-center gap-2 text-sm">
            <a
              href={det.video_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1"
            >
              <ExternalLink className="h-3 w-3" />
              動画を確認
            </a>
            {det.video_date && (
              <span className="text-muted-foreground">
                ({new Date(det.video_date).toLocaleDateString("ja-JP")})
              </span>
            )}
          </div>
        )}

        {/* レビュー済み情報 */}
        {det.reviewed_at && det.review_note && (
          <div className="bg-muted/50 rounded-md px-3 py-2 text-sm">
            <span className="text-muted-foreground">レビューメモ: </span>
            {det.review_note}
          </div>
        )}

        {/* 展開時: レビューフォーム */}
        {expanded && (
          <div className="border-t pt-3 space-y-3">
            {/* スクリーンショット */}
            {det.screenshot_path && (
              <div>
                <p className="text-xs text-muted-foreground mb-1">
                  検出時スクリーンショット
                </p>
                <div className="bg-muted rounded-lg p-4 text-center text-sm text-muted-foreground">
                  {det.screenshot_path}
                </div>
              </div>
            )}

            {/* 議員ID入力 */}
            <div className="flex items-center gap-2">
              <label className="text-sm text-muted-foreground whitespace-nowrap">
                議員ID:
              </label>
              <Input
                type="number"
                placeholder="議員IDを入力（手動紐付け）"
                value={memberIdInput}
                onChange={(e) => setMemberIdInput(e.target.value)}
                className="max-w-40"
              />
              {det.identified_by && (
                <Badge variant="outline" className="text-xs">
                  {det.identified_by === "manual"
                    ? "手動紐付け"
                    : det.identified_by === "face_recognition"
                      ? "顔認識"
                      : det.identified_by}
                </Badge>
              )}
            </div>

            {/* メモ入力 */}
            <div>
              <label className="text-sm text-muted-foreground block mb-1">
                レビューメモ:
              </label>
              <Input
                placeholder="判断の根拠をメモ（任意）"
                value={note}
                onChange={(e) => setNote(e.target.value)}
              />
            </div>

            {/* アクションボタン */}
            <div className="flex items-center gap-2 pt-1">
              <Button
                variant="destructive"
                size="sm"
                onClick={() => handleSubmit("approved")}
                disabled={isSubmitting}
              >
                <CheckCircle2 className="h-4 w-4 mr-1" />
                居眠り確定（ペナルティ適用）
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleSubmit("rejected")}
                disabled={isSubmitting}
              >
                <XCircle className="h-4 w-4 mr-1" />
                却下（居眠りではない）
              </Button>
            </div>

            {det.review_status !== "pending" && (
              <p className="text-xs text-muted-foreground">
                ステータスを変更すると該当議員のスコアが自動で再計算されます
              </p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
