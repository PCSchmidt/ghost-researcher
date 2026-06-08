"use client";

import { useMemo, useState } from "react";
import { Activity, Database, FileText, Globe2, Server } from "lucide-react";
import { JobStatus } from "@/components/JobStatus";
import { ReportViewer } from "@/components/ReportViewer";
import { ResearchForm } from "@/components/ResearchForm";
import { SourceCard } from "@/components/SourceCard";
import { submitResearchGoal, type ResearchJob } from "@/lib/api";

export function ResearchWorkspace() {
  const [job, setJob] = useState<ResearchJob | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(researchGoal: string) {
    setIsSubmitting(true);
    setError(null);
    try {
      setJob(await submitResearchGoal(researchGoal));
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Research request failed");
    } finally {
      setIsSubmitting(false);
    }
  }

  const sourceUrls = useMemo(() => job?.session.sources_visited ?? [], [job]);

  return (
    <main className="min-h-screen bg-[#f7f7f4] text-zinc-950">
      <div className="mx-auto grid min-h-screen w-full max-w-7xl grid-cols-1 gap-0 lg:grid-cols-[380px_1fr]">
        <aside className="border-b border-zinc-200 bg-white px-5 py-5 lg:border-b-0 lg:border-r">
          <div className="mb-6 flex items-center gap-3">
            <div className="flex size-10 items-center justify-center rounded-md bg-zinc-950 text-white">
              <Globe2 size={20} aria-hidden="true" />
            </div>
            <div>
              <h1 className="text-lg font-semibold tracking-normal">GhostResearcher</h1>
              <p className="text-sm text-zinc-600">Agentic web research workspace</p>
            </div>
          </div>

          <ResearchForm onSubmit={handleSubmit} isSubmitting={isSubmitting} />

          {error ? (
            <div role="alert" className="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
              {error}
            </div>
          ) : null}

          <section className="mt-6 border-t border-zinc-200 pt-5" aria-label="Run summary">
            <div className="grid grid-cols-2 gap-3">
              <Metric icon={<Activity size={16} />} label="Steps" value={String(job?.session.steps_taken ?? 0)} />
              <Metric icon={<Database size={16} />} label="Sources" value={String(sourceUrls.length)} />
              <Metric icon={<Server size={16} />} label="State" value={job?.session.termination_state ?? "idle"} />
              <Metric icon={<FileText size={16} />} label="Report" value={job?.synthesis ? "ready" : "pending"} />
            </div>
          </section>

          <JobStatus key={job?.job_id ?? "idle"} jobId={job?.job_id ?? null} initialEvents={job?.status_events ?? []} />
        </aside>

        <section className="px-5 py-5 lg:px-8" aria-label="Research output">
          <div className="mb-5 flex flex-col gap-2 border-b border-zinc-200 pb-4 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-teal-700">Current run</p>
              <h2 className="mt-1 text-2xl font-semibold tracking-normal text-zinc-950">
                {job?.session.research_goal ?? "Submit a research goal"}
              </h2>
            </div>
            <div className="text-sm text-zinc-600">{job ? `Job ${job.job_id.slice(0, 8)}` : "No job yet"}</div>
          </div>

          <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_320px]">
            <ReportViewer report={job?.synthesis ?? null} />
            <section aria-label="Sources" className="space-y-3">
              <h3 className="text-sm font-semibold uppercase tracking-[0.12em] text-zinc-600">Sources</h3>
              {sourceUrls.length ? (
                sourceUrls.map((url) => (
                  <SourceCard
                    key={url}
                    url={url}
                    evidenceRecords={job?.session.evidence_records ?? []}
                    toolResults={job?.tool_results ?? []}
                  />
                ))
              ) : (
                <div className="rounded-md border border-dashed border-zinc-300 bg-white px-4 py-6 text-sm text-zinc-600">
                  Sources will appear after navigation and credibility assessment.
                </div>
              )}
            </section>
          </div>
        </section>
      </div>
    </main>
  );
}

function Metric({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="rounded-md border border-zinc-200 bg-zinc-50 px-3 py-3">
      <div className="mb-2 flex items-center gap-2 text-zinc-500">
        {icon}
        <span className="text-xs font-medium uppercase tracking-[0.12em]">{label}</span>
      </div>
      <div className="truncate text-sm font-semibold text-zinc-950">{value}</div>
    </div>
  );
}
