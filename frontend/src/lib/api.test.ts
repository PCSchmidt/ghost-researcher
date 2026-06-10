import { afterEach, describe, expect, it, vi } from "vitest";
import { apiBaseUrl, getResearchJob, statusEventsUrl, submitResearchGoal } from "@/lib/api";

afterEach(() => {
  vi.unstubAllEnvs();
  vi.restoreAllMocks();
});

describe("api client", () => {
  it("uses localhost backend by default", () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "");

    expect(apiBaseUrl()).toBe("http://localhost:8000");
    expect(statusEventsUrl("job-1")).toBe("http://localhost:8000/research/job-1/events");
  });

  it("submits a research goal to the backend", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "https://api.example.com/");
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ job_id: "job-1" }) });
    vi.stubGlobal("fetch", fetchMock);

    await expect(submitResearchGoal("Find FAA guidance")).resolves.toEqual({ job_id: "job-1" });

    expect(fetchMock).toHaveBeenCalledWith("https://api.example.com/research", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ research_goal: "Find FAA guidance" }),
    });
  });

  it("raises a useful error when the backend rejects a request", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 422 }));

    await expect(submitResearchGoal(" ")).rejects.toThrow("Research request failed with status 422");
  });

  it("fetches a job by id for polling", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "https://api.example.com");
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ job_id: "job-1", status: "running" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(getResearchJob("job-1")).resolves.toEqual({ job_id: "job-1", status: "running" });
    expect(fetchMock).toHaveBeenCalledWith("https://api.example.com/research/job-1");
  });

  it("surfaces the backend error detail when present", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => ({ detail: "connect_over_cdp timeout" }),
      }),
    );

    await expect(submitResearchGoal("Find FAA guidance")).rejects.toThrow(
      "Research request failed (status 500): connect_over_cdp timeout",
    );
  });
});