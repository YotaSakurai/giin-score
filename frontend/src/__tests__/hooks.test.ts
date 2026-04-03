import { describe, it, expect } from "vitest";
import { buildQuery } from "../lib/api";

describe("buildQuery for member filters", () => {
  it("builds basic filter params", () => {
    const qs = buildQuery({ chamber: "representatives", page: 1 });
    expect(qs).toBe("?chamber=representatives&page=1");
  });

  it("omits undefined and empty values", () => {
    const qs = buildQuery({ chamber: undefined, party: "", search: "田中" });
    expect(qs).not.toContain("chamber");
    expect(qs).not.toContain("party");
    expect(qs).toContain("search=");
  });

  it("handles grade comma-separated values", () => {
    const qs = buildQuery({ grade: "A,B" });
    expect(qs).toContain("grade=A%2CB");
  });

  it("handles score range params", () => {
    const qs = buildQuery({ score_min: 40, score_max: 80 });
    expect(qs).toContain("score_min=40");
    expect(qs).toContain("score_max=80");
  });

  it("handles axis range params", () => {
    const qs = buildQuery({
      la_min: 30,
      vb_max: 90,
      qq_min: 50,
    });
    expect(qs).toContain("la_min=30");
    expect(qs).toContain("vb_max=90");
    expect(qs).toContain("qq_min=50");
  });

  it("handles sort params", () => {
    const qs = buildQuery({ sort_by: "total", sort_order: "asc" });
    expect(qs).toContain("sort_by=total");
    expect(qs).toContain("sort_order=asc");
  });

  it("returns empty string for no params", () => {
    expect(buildQuery({})).toBe("");
    expect(buildQuery()).toBe("");
  });
});
