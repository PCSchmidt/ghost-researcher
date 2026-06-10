import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ReportViewer } from "@/components/ReportViewer";

describe("ReportViewer", () => {
  it("renders report findings and confidence", () => {
    render(
      <ReportViewer
        report={{
          title: "FAA guidance",
          summary: "Current guidance summary",
          confidence: 0.82,
          sources_used: ["https://example.com"],
          key_findings: [{ text: "Finding with source", source_urls: ["https://example.com"] }],
        }}
      />,
    );

    expect(screen.getByText("FAA guidance")).toBeInTheDocument();
    expect(screen.getByText("82%")).toBeInTheDocument();
    expect(screen.getByText("Finding with source")).toBeInTheDocument();
  });

  it("renders a long-form paper with sections, citations, and references", () => {
    render(
      <ReportViewer
        report={{
          title: "Data Center Efficiency 2025",
          summary: "abstract text",
          confidence: 0.75,
          sources_used: ["https://a.gov/x", "https://b.org/y"],
          key_findings: [{ text: "k", source_urls: ["https://a.gov/x"] }],
          abstract: "This paper surveys efficiency strategies.",
          sections: [
            {
              heading: "Cooling",
              paragraphs: [{ text: "Direct-to-chip cooling lowers PUE.", citations: ["https://a.gov/x"] }],
            },
          ],
          conclusion: "Cooling drives the largest gains.",
          references: [
            { url: "https://a.gov/x", title: "Cooling study", credibility_score: 0.9 },
            { url: "https://b.org/y", title: "Adoption report", credibility_score: 0.6 },
          ],
        }}
      />,
    );

    expect(screen.getByText("Abstract")).toBeInTheDocument();
    expect(screen.getByText("1. Cooling")).toBeInTheDocument();
    expect(screen.getByText(/Direct-to-chip cooling lowers PUE\./)).toBeInTheDocument();
    expect(screen.getByText("Conclusion")).toBeInTheDocument();
    expect(screen.getByText("References")).toBeInTheDocument();
    expect(screen.getByText("Cooling study")).toBeInTheDocument();
    // in-text citation marker maps the URL to reference number [1]
    // (also appears as the reference list number, so assert at least one)
    expect(screen.getAllByText("[1]").length).toBeGreaterThanOrEqual(1);
  });
});