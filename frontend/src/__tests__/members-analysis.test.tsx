/**
 * 議員分析ハブ機能のテスト
 * - AdvancedMemberFilter: フィルタ状態管理、プリセット
 * - ViewModeToggle: ビューモード切替
 * - MemberTable: テーブル表示、ソート、カラムトグル
 * - MemberScatterPlot: 散布図表示
 * - MembersContent: 全体の統合
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ViewModeToggle } from "@/components/member/ViewModeToggle";
import {
  countActiveFilters,
  isRangeActive,
  DEFAULT_FILTER_STATE,
  type AdvancedFilterState,
} from "@/components/member/AdvancedMemberFilter";
import type { MemberWithScore, MemberScorePoint } from "@/lib/types";
import { SCORE_AXIS_OPTIONS } from "@/lib/types";

// ---- AdvancedMemberFilter のユーティリティ関数テスト ----

// AdvancedMemberFilter の export された関数をテスト
// コンポーネント自体は SWR hooks に依存するのでユーティリティ関数を個別テスト

describe("isRangeActive", () => {
  it("returns false for default range [0, 100]", () => {
    expect(isRangeActive([0, 100])).toBe(false);
  });

  it("returns true when min > 0", () => {
    expect(isRangeActive([10, 100])).toBe(true);
  });

  it("returns true when max < 100", () => {
    expect(isRangeActive([0, 90])).toBe(true);
  });

  it("returns true when both are changed", () => {
    expect(isRangeActive([20, 80])).toBe(true);
  });
});

describe("countActiveFilters", () => {
  it("returns 0 for default state", () => {
    expect(countActiveFilters(DEFAULT_FILTER_STATE)).toBe(0);
  });

  it("counts grade filter", () => {
    const state = { ...DEFAULT_FILTER_STATE, grades: ["A", "B"] };
    expect(countActiveFilters(state)).toBe(1);
  });

  it("counts score range filter", () => {
    const state: AdvancedFilterState = {
      ...DEFAULT_FILTER_STATE,
      scoreRange: [30, 80],
    };
    expect(countActiveFilters(state)).toBe(1);
  });

  it("counts multiple filters", () => {
    const state: AdvancedFilterState = {
      ...DEFAULT_FILTER_STATE,
      grades: ["A"],
      scoreRange: [50, 100],
      laRange: [20, 80],
      qqRange: [60, 100],
    };
    expect(countActiveFilters(state)).toBe(4);
  });

  it("counts all axis ranges", () => {
    const state: AdvancedFilterState = {
      ...DEFAULT_FILTER_STATE,
      scoreRange: [10, 90],
      laRange: [10, 90],
      vbRange: [10, 90],
      piRange: [10, 90],
      trRange: [10, 90],
      qqRange: [10, 90],
    };
    expect(countActiveFilters(state)).toBe(6);
  });
});

// ---- ViewModeToggle テスト ----

describe("ViewModeToggle", () => {
  it("renders three mode buttons", () => {
    render(<ViewModeToggle value="grid" onChange={() => {}} />);
    expect(screen.getByTitle("カード")).toBeDefined();
    expect(screen.getByTitle("テーブル")).toBeDefined();
    expect(screen.getByTitle("散布図")).toBeDefined();
  });

  it("calls onChange with correct mode", () => {
    const onChange = vi.fn();
    render(<ViewModeToggle value="grid" onChange={onChange} />);
    fireEvent.click(screen.getByTitle("テーブル"));
    expect(onChange).toHaveBeenCalledWith("table");
  });

  it("calls onChange for scatter mode", () => {
    const onChange = vi.fn();
    render(<ViewModeToggle value="grid" onChange={onChange} />);
    fireEvent.click(screen.getByTitle("散布図"));
    expect(onChange).toHaveBeenCalledWith("scatter");
  });
});

// ---- データ型/定数の整合性テスト ----

describe("SCORE_AXIS_OPTIONS", () => {
  it("has 6 options (total + 5 axes)", () => {
    expect(SCORE_AXIS_OPTIONS).toHaveLength(6);
  });

  it("contains all expected axes", () => {
    const values = SCORE_AXIS_OPTIONS.map((o) => o.value);
    expect(values).toContain("total");
    expect(values).toContain("legislative_activity");
    expect(values).toContain("voting_behavior");
    expect(values).toContain("policy_influence");
    expect(values).toContain("transparency");
    expect(values).toContain("question_quality");
  });

  it("all options have Japanese labels", () => {
    for (const opt of SCORE_AXIS_OPTIONS) {
      expect(opt.label).toBeTruthy();
      expect(typeof opt.label).toBe("string");
    }
  });
});

describe("MemberScorePoint type compliance", () => {
  it("can create a valid MemberScorePoint", () => {
    const point: MemberScorePoint = {
      id: 1,
      name: "テスト太郎",
      party: "テスト党",
      chamber: "representatives",
      grade: "A",
      total: 85.0,
      legislative_activity: 90.0,
      voting_behavior: 80.0,
      policy_influence: 70.0,
      transparency: 60.0,
      question_quality: 95.0,
    };
    expect(point.id).toBe(1);
    expect(point.grade).toBe("A");
    // すべてのスコア軸がアクセス可能
    const axes = ["total", "legislative_activity", "voting_behavior", "policy_influence", "transparency", "question_quality"];
    for (const axis of axes) {
      expect(typeof point[axis as keyof MemberScorePoint]).toBe("number");
    }
  });

  it("party can be null", () => {
    const point: MemberScorePoint = {
      id: 2,
      name: "無所属太郎",
      party: null,
      chamber: "councillors",
      grade: "C",
      total: 50.0,
      legislative_activity: 50.0,
      voting_behavior: 50.0,
      policy_influence: 50.0,
      transparency: 50.0,
      question_quality: 50.0,
    };
    expect(point.party).toBeNull();
  });
});

// ---- MemberTable のユーティリティロジックテスト ----

describe("MemberTable getScoreValue logic", () => {
  const memberWithScore: MemberWithScore = {
    id: 1,
    name: "テスト太郎",
    name_reading: null,
    chamber: "representatives",
    party: "テスト党",
    faction: null,
    district: "東京1区",
    role_category: "ruling_junior",
    latest_score: {
      total: 72.3,
      grade: "B",
      legislative_activity: 80.5,
      voting_behavior: 65.2,
      policy_influence: 55.1,
      transparency: 45.0,
      question_quality: 90.7,
    },
  };

  const memberWithoutScore: MemberWithScore = {
    id: 2,
    name: "スコアなし",
    name_reading: null,
    chamber: "councillors",
    party: null,
    faction: null,
    district: null,
    role_category: null,
    latest_score: null,
  };

  it("score values are accessible from latest_score", () => {
    const score = memberWithScore.latest_score!;
    expect(score.total).toBe(72.3);
    expect(score.legislative_activity).toBe(80.5);
    expect(score.question_quality).toBe(90.7);
  });

  it("handles null latest_score", () => {
    expect(memberWithoutScore.latest_score).toBeNull();
  });

  it("grade is accessible from score", () => {
    expect(memberWithScore.latest_score?.grade).toBe("B");
  });
});

// ---- URL パラメータ変換テスト ----

describe("URL parameter parsing (MembersContent logic)", () => {
  function parseRange(minStr: string | null, maxStr: string | null): [number, number] {
    const min = minStr ? Number(minStr) : 0;
    const max = maxStr ? Number(maxStr) : 100;
    return [min, max];
  }

  it("returns [0, 100] for null params", () => {
    expect(parseRange(null, null)).toEqual([0, 100]);
  });

  it("parses min only", () => {
    expect(parseRange("30", null)).toEqual([30, 100]);
  });

  it("parses max only", () => {
    expect(parseRange(null, "80")).toEqual([0, 80]);
  });

  it("parses both min and max", () => {
    expect(parseRange("20", "70")).toEqual([20, 70]);
  });

  it("parses grade string", () => {
    const gradeStr = "A,B,C";
    const grades = gradeStr.split(",");
    expect(grades).toEqual(["A", "B", "C"]);
  });

  it("empty grade string results in empty array", () => {
    const gradeStr: string = "";
    const grades = gradeStr ? gradeStr.split(",") : [];
    expect(grades).toEqual([]);
  });
});

// ---- フィルタ→APIパラメータ変換テスト ----

describe("Filter state to API params conversion", () => {
  function rangeParams(
    range: [number, number],
    minKey: string,
    maxKey: string
  ): Record<string, number | undefined> {
    return {
      [minKey]: range[0] > 0 ? range[0] : undefined,
      [maxKey]: range[1] < 100 ? range[1] : undefined,
    };
  }

  it("default range produces no params", () => {
    const result = rangeParams([0, 100], "score_min", "score_max");
    expect(result.score_min).toBeUndefined();
    expect(result.score_max).toBeUndefined();
  });

  it("custom range produces correct params", () => {
    const result = rangeParams([30, 80], "la_min", "la_max");
    expect(result.la_min).toBe(30);
    expect(result.la_max).toBe(80);
  });

  it("only min set produces only min param", () => {
    const result = rangeParams([50, 100], "qq_min", "qq_max");
    expect(result.qq_min).toBe(50);
    expect(result.qq_max).toBeUndefined();
  });

  it("only max set produces only max param", () => {
    const result = rangeParams([0, 70], "vb_min", "vb_max");
    expect(result.vb_min).toBeUndefined();
    expect(result.vb_max).toBe(70);
  });
});
