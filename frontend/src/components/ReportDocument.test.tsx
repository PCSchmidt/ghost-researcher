import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ReportDocument } from "@/components/ReportDocument";

describe("ReportDocument", () => {
  it("renders a long-form paper with numbered sections and references", () => {
    render(
      <ReportDocument
        meta="Confidence 75%"
        report={{
          title: "Data Center Efficiency 2025",
          summary: "abstract",
          confidence: 0.75,
          sources_used: ["https://a.gov/x"],
          key_findings: [{ text: "k", source_urls: ["https://a.gov/x"] }],
          abstract: "This paper surveys efficiency strategies.",
          sections: [
            { heading: "Cooling", paragraphs: [{ text: "Direct-to-chip cooling lowers PUE.", citations: ["https://a.gov/x"] }] },
          ],
          conclusion: "Cooling drives the largest gains.",
          references: [{ url: "https://a.gov/x", title: "Cooling study", credibility_score: 0.9 }],
        }}
      />,
    );

    expect(screen.getByText("Data Center Efficiency 2025")).toBeInTheDocument();
    expect(screen.getByText("Abstract")).toBeInTheDocument();
    expect(screen.getByText("1. Cooling")).toBeInTheDocument();
    expect(screen.getByText("Conclusion")).toBeInTheDocument();
    expect(screen.getByText("Cooling study")).toBeInTheDocument();
    expect(screen.getAllByText("[1]").length).toBeGreaterThanOrEqual(1);
  });

  it("renders a flat report (no sections) as summary + findings", () => {
    render(
      <ReportDocument
        report={{
          title: "Flat brief",
          summary: "A short summary.",
          confidence: 0.5,
          sources_used: ["https://a.gov/x"],
          key_findings: [{ text: "A key finding.", source_urls: ["https://a.gov/x"] }],
        }}
      />,
    );

    expect(screen.getByText("Flat brief")).toBeInTheDocument();
    expect(screen.getByText("A short summary.")).toBeInTheDocument();
    expect(screen.getByText("A key finding.")).toBeInTheDocument();
  });
});
