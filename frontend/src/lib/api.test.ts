import { afterEach, describe, expect, it, vi } from "vitest";
import { apiBaseUrl, statusEventsUrl, submitResearchGoal } from "@/lib/api";

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
});