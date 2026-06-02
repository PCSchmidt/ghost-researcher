import { FileText } from "lucide-react";
import type { ResearchReport } from "@/lib/api";

export function ReportViewer({ report }: { report: ResearchReport | null }) {
  if (!report) {
    return (
      <section className="rounded-md border border-dashed border-zinc-300 bg-white p-5" aria-label="Report">
        <div className="mb-4 flex size-10 items-center justify-center rounded-md bg-amber-50 text-amber-800">
          <FileText size={20} aria-hidden="true" />
        </div>
        <h3 className="text-lg font-semibold text-zinc-950">Report pending</h3>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-zinc-600">
          A source-traced report appears when the planner reaches sufficient coverage.
        </p>
      </section>
    );
  }

  return (
    <section className="rounded-md border border-zinc-200 bg-white p-5" aria-label="Report">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-teal-700">Report</p>
          <h3 className="mt-1 text-xl font-semibold text-zinc-950">{report.title}</h3>
        </div>
        <div className="rounded-md border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm font-semibold text-zinc-800">
          {Math.round(report.confidence * 100)}%
        </div>
      </div>
      <p className="text-sm leading-6 text-zinc-700">{report.summary}</p>
      <div className="mt-5 space-y-3">
        {report.key_findings.map((finding) => (
          <article key={finding.text} className="rounded-md border border-zinc-200 bg-zinc-50 px-4 py-3">
            <p className="text-sm font-medium leading-6 text-zinc-950">{finding.text}</p>
            <p className="mt-2 text-xs text-zinc-600">{finding.source_urls.join(", ")}</p>
          </article>
        ))}
      </div>
    </section>
  );
}