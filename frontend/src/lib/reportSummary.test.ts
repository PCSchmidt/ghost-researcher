import { describe, expect, it } from "vitest";
import { deriveReportMeta, truncate } from "@/lib/reportSummary";
import type { ResearchJob } from "@/lib/api";

function jobWith(overrides: Partial<ResearchJob> = {}): ResearchJob {
  return {
    job_id: "job-1",
    created_at: "2026-06-12T00:00:00Z",
    updated_at: "2026-06-12T00:05:00Z",
    status: "completed",
    status_events: [],
    session: {
      research_goal: "Effects of portable nuclear reactors on data centers",
      steps_taken: 5,
      planner_turns: 5,
      running_tokens: 0,
      running_cost_usd: 0,
      sources_visited: ["https://a.example", "https://b.example"],
      current_source_url: null,
      search_queries: [],
      source_candidates: [],
      termination_state: "finalized",
      termination_reason: "sufficient_coverage",
      evidence_quality: {
        sources_visited_count: 2,
        assessed_evidence_count: 2,
        extracted_evidence_count: 0,
        navigation_fallback_evidence_count: 0,
        average_assessed_credibility: 0.7,
        detection_event_count: 0,
      },
      evidence_records: [],
    },
    decisions: [],
    tool_results: [],
    synthesis: null,
    ...overrides,
  };
}

describe("deriveReportMeta", () => {
  it("prefers the report title and abstract for a long-form paper", () => {
    const job = jobWith({
      synthesis: {
        title: "Portable Nuclear Power for Data Centers",
        summary: "short summary",
        key_findings: [],
        sources_used: [],
        confidence: 0.72,
        abstract: "This paper examines operational expectations for SMR deployments.",
        sections: [{ heading: "Background", paragraphs: [] }],
        conclusion: "",
        references: [],
      },
    });

    const meta = deriveReportMeta(job);

    expect(meta.title).toBe("Portable Nuclear Power for Data Centers");
    expect(meta.description).toBe("This paper examines operational expectations for SMR deployments.");
    expect(meta.confidencePct).toBe(72);
    expect(meta.sourceCount).toBe(2);
    expect(meta.isLongForm).toBe(true);
  });

  it("falls back to the research goal when no report exists", () => {
    const meta = deriveReportMeta(jobWith());

    expect(meta.title).toBe("Effects of portable nuclear reactors on data centers");
    expect(meta.description).toBe("Effects of portable nuclear reactors on data centers");
    expect(meta.confidencePct).toBeNull();
    expect(meta.isLongForm).toBe(false);
  });

  it("uses the flat summary when there is no abstract", () => {
    const job = jobWith({
      synthesis: {
        title: "Flat Report",
        summary: "A concise synthesized summary of the findings.",
        key_findings: [],
        sources_used: [],
        confidence: 0.4,
      },
    });

    const meta = deriveReportMeta(job);

    expect(meta.description).toBe("A concise synthesized summary of the findings.");
    expect(meta.isLongForm).toBe(false);
  });
});

describe("truncate", () => {
  it("collapses whitespace and leaves short strings intact", () => {
    expect(truncate("  hello   world ", 50)).toBe("hello world");
  });

  it("clips long strings with an ellipsis at the limit", () => {
    const result = truncate("a".repeat(120), 20);
    expect(result).toHaveLength(20);
    expect(result.endsWith("…")).toBe(true);
  });
});
