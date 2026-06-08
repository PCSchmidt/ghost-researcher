import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SourceCard } from "@/components/SourceCard";

describe("SourceCard", () => {
  it("renders assessed credibility from session evidence", () => {
    render(
      <SourceCard
        url="https://faa.gov/report"
        evidenceRecords={[
          {
            url: "https://faa.gov/report",
            title: "FAA Report",
            claims_count: 1,
            credibility_score: 0.91,
            evidence_type: "navigation_fallback",
          },
          {
            url: "https://faa.gov/report",
            title: "FAA Report",
            claims_count: 1,
            credibility_score: 0.84,
            evidence_type: "assessed",
          },
        ]}
        toolResults={[]}
      />,
    );

    expect(screen.getByText("faa.gov")).toBeInTheDocument();
    expect(screen.getByText("Credibility 84%")).toBeInTheDocument();
  });

  it("falls back to legacy credibility tool results", () => {
    render(
      <SourceCard
        url="https://example.com/report"
        evidenceRecords={[]}
        toolResults={[{ url: "https://example.com/report", score: 0.72 }]}
      />,
    );

    expect(screen.getByText("Credibility 72%")).toBeInTheDocument();
  });

  it("shows pending when no evidence score is available", () => {
    render(<SourceCard url="https://example.com/report" evidenceRecords={[]} toolResults={[]} />);

    expect(screen.getByText("Credibility pending")).toBeInTheDocument();
  });
});
