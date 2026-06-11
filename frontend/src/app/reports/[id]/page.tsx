"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Download, LoaderCircle } from "lucide-react";
import { ReportDocument } from "@/components/ReportDocument";
import { getResearchJob, type ResearchJob } from "@/lib/api";

export default function ReportPermalinkPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [job, setJob] = useState<ResearchJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    getResearchJob(id)
      .then((loaded) => {
        if (!cancelled) {
          setJob(loaded);
          setLoading(false);
        }
      })
      .catch((currentError: unknown) => {
        if (!cancelled) {
          setError(currentError instanceof Error ? currentError.message : "Failed to load report");
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  const report = job?.synthesis ?? null;
  const meta = job
    ? [
        report ? `Confidence ${Math.round(report.confidence * 100)}%` : null,
        job.created_at ? new Date(job.created_at).toLocaleDateString() : null,
        `${job.session?.sources_visited?.length ?? 0} sources`,
      ]
        .filter(Boolean)
        .join("  ·  ")
    : "";

  return (
    <main className="min-h-screen bg-zinc-100">
      <div className="no-print sticky top-0 z-10 border-b border-zinc-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-[820px] items-center justify-between px-5 py-3">
          <Link href="/" className="inline-flex items-center gap-1.5 text-sm font-medium text-zinc-700 hover:text-zinc-950">
            <ArrowLeft size={16} aria-hidden="true" /> Workspace
          </Link>
          {report ? (
            <button
              type="button"
              onClick={() => window.print()}
              className="inline-flex h-9 items-center gap-2 rounded-md bg-zinc-950 px-3.5 text-sm font-semibold text-white transition hover:bg-zinc-800"
            >
              <Download size={16} aria-hidden="true" /> Download / Print PDF
            </button>
          ) : null}
        </div>
      </div>

      <div className="mx-auto max-w-[820px] px-4 py-8">
        <div className="report-sheet rounded-lg border border-zinc-200 bg-white shadow-sm">
          {loading ? (
            <Centered>
              <LoaderCircle size={22} className="animate-spin text-zinc-500" aria-hidden="true" />
              <p className="mt-3 text-sm text-zinc-600">Loading report…</p>
            </Centered>
          ) : error ? (
            <Centered>
              <p className="text-sm font-medium text-red-700">{error}</p>
              <Link href="/" className="mt-3 text-sm text-teal-700 hover:underline">
                Back to workspace
              </Link>
            </Centered>
          ) : job && job.status === "running" ? (
            <Centered>
              <LoaderCircle size={22} className="animate-spin text-teal-600" aria-hidden="true" />
              <p className="mt-3 text-sm text-zinc-600">This research job is still running. Refresh in a minute.</p>
            </Centered>
          ) : report ? (
            <ReportDocument report={report} meta={meta} />
          ) : (
            <Centered>
              <p className="text-sm text-zinc-600">No report was produced for this job.</p>
              {job?.session?.research_goal ? (
                <p className="mt-2 max-w-md text-center text-xs text-zinc-500">Goal: {job.session.research_goal}</p>
              ) : null}
            </Centered>
          )}
        </div>
      </div>
    </main>
  );
}

function Centered({ children }: { children: React.ReactNode }) {
  return <div className="flex min-h-[320px] flex-col items-center justify-center px-6 py-16 text-center">{children}</div>;
}
