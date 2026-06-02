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
});