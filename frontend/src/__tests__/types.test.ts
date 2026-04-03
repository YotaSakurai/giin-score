import { describe, it, expect } from "vitest";
import {
  GRADE_COLORS,
  AXIS_LABELS,
  SCORE_AXIS_OPTIONS,
} from "../lib/types";

describe("types constants", () => {
  it("GRADE_COLORS has all 5 grades", () => {
    const grades = ["A", "B", "C", "D", "F"];
    for (const g of grades) {
      expect(GRADE_COLORS[g]).toBeDefined();
      expect(GRADE_COLORS[g]).toMatch(/^bg-/);
    }
  });

  it("AXIS_LABELS has all 5 axes", () => {
    const axes = [
      "legislative_activity",
      "voting_behavior",
      "policy_influence",
      "transparency",
      "question_quality",
    ];
    for (const a of axes) {
      expect(AXIS_LABELS[a]).toBeDefined();
      expect(typeof AXIS_LABELS[a]).toBe("string");
    }
  });

  it("SCORE_AXIS_OPTIONS includes total and all 5 axes", () => {
    expect(SCORE_AXIS_OPTIONS).toHaveLength(6);
    const values = SCORE_AXIS_OPTIONS.map((o) => o.value);
    expect(values).toContain("total");
    expect(values).toContain("legislative_activity");
    expect(values).toContain("question_quality");
  });
});
