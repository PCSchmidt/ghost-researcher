"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, FileText, LoaderCircle } from "lucide-react";
import { getReportsList, reportPermalink, type ReportSummary } from "@/lib/api";

export default function ReportsListPage() {
  const [reports, setReports] = useState<ReportSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getReportsList()
      .then((rows) => !cancelled && setReports(rows))
      .catch((currentError: unknown) => !cancelled && setError(currentError instanceof Error ? currentError.message : "Failed to load reports"));
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main className="min-h-screen bg-[#f7f7f4]">
      <div className="mx-auto max-w-3xl px-5 py-8">
        <Link href="/" className="inline-flex items-center gap-1.5 text-sm font-medium text-zinc-700 hover:text-zinc-950">
          <ArrowLeft size={16} aria-hidden="true" /> Workspace
        </Link>
        <h1 className="mt-4 text-2xl font-semibold tracking-tight text-zinc-950">Reports</h1>
        <p className="mt-1 text-sm text-zinc-600">Every research run, newest first. Open one to read or export as PDF.</p>

        <div className="mt-6 space-y-3">
          {error ? (
            <p className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{error}</p>
          ) : reports === null ? (
            <div className="flex items-center gap-2 text-sm text-zinc-600">
              <LoaderCircle size={16} className="animate-spin" aria-hidden="true" /> Loading…
            </div>
          ) : reports.length === 0 ? (
            <p className="rounded-md border border-dashed border-zinc-300 bg-white px-4 py-6 text-sm text-zinc-600">
              No reports yet. Run a research goal in the workspace.
            </p>
          ) : (
            reports.map((report) => (
              <Link
                key={report.job_id}
                href={reportPermalink(report.job_id)}
                className="block rounded-md border border-zinc-200 bg-white px-4 py-3 transition hover:border-zinc-400"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="flex items-center gap-2 truncate text-sm font-semibold text-zinc-950">
                      <FileText size={15} className="shrink-0 text-zinc-500" aria-hidden="true" />
                      {report.title || report.research_goal || "Untitled report"}
                    </p>
                    {report.research_goal && report.title ? (
                      <p className="mt-1 truncate text-xs text-zinc-500">{report.research_goal}</p>
                    ) : null}
                  </div>
                  <div className="shrink-0 text-right text-xs text-zinc-500">
                    <div>{report.confidence != null ? `${Math.round(report.confidence * 100)}%` : report.status}</div>
                    <div className="mt-0.5">{report.source_count} sources{report.is_long_form ? " · paper" : ""}</div>
                  </div>
                </div>
              </Link>
            ))
          )}
        </div>
      </div>
    </main>
  );
}
