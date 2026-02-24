import { describe, it, expect, vi, beforeEach } from "vitest";

const API_BASE = "http://localhost:8000/api/v1";

// fetchApi is not exported, so we test it indirectly through the exported functions
// by mocking global fetch.

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("fetchApi (via exported functions)", () => {
  it("getSessions fetches from /sessions and returns data", async () => {
    const mockSessions = [
      { session_number: 213, name: "第213回国会" },
      { session_number: 212, name: "第212回国会" },
    ];

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockSessions),
    });

    // Dynamic import to ensure fetch mock is in place
    const { getSessions } = await import("../lib/api");
    const result = await getSessions();

    expect(global.fetch).toHaveBeenCalledWith(
      `${API_BASE}/sessions`,
      expect.objectContaining({
        headers: expect.objectContaining({
          "Content-Type": "application/json",
        }),
      })
    );
    expect(result).toEqual(mockSessions);
  });

  it("throws an error when the API returns a non-ok response", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      statusText: "Not Found",
    });

    const { getSessions } = await import("../lib/api");

    await expect(getSessions()).rejects.toThrow("API error: 404 Not Found");
  });

  it("getMembers builds query string from params", async () => {
    const mockResponse = { items: [], total: 0, page: 1, per_page: 20 };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    });

    const { getMembers } = await import("../lib/api");
    await getMembers({ chamber: "衆議院", page: 2 });

    const callUrl = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    expect(callUrl).toContain("chamber=%E8%A1%86%E8%AD%B0%E9%99%A2");
    expect(callUrl).toContain("page=2");
  });

  it("getMembers omits undefined and empty params", async () => {
    const mockResponse = { items: [], total: 0, page: 1, per_page: 20 };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    });

    const { getMembers } = await import("../lib/api");
    await getMembers({ chamber: undefined, party: "", search: "田中" });

    const callUrl = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    expect(callUrl).not.toContain("chamber");
    expect(callUrl).not.toContain("party");
    expect(callUrl).toContain("search=");
  });
});
