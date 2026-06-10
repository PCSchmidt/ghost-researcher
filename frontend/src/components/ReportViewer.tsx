import { FileText, LoaderCircle } from "lucide-react";
import type { Reference, ReportParagraph, ResearchReport } from "@/lib/api";

export function ReportViewer({ report, isRunning = false }: { report: ResearchReport | null; isRunning?: boolean }) {
  if (!report) {
    if (isRunning) {
      return (
        <section className="rounded-md border border-teal-200 bg-teal-50/40 p-5" aria-label="Report" aria-busy="true">
          <div className="mb-4 flex size-10 items-center justify-center rounded-md bg-teal-100 text-teal-800">
            <LoaderCircle size={20} className="animate-spin" aria-hidden="true" />
          </div>
          <h3 className="text-lg font-semibold text-zinc-950">Researching…</h3>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-zinc-600">
            The agent is searching, navigating sources, and assessing credibility. Steps and sources
            appear in the status panel as they complete — the report renders here when coverage is
            sufficient. This usually takes 1–3 minutes.
          </p>
        </section>
      );
    }
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

  const isLongForm = Boolean(report.sections && report.sections.length > 0);

  return (
    <section className="rounded-md border border-zinc-200 bg-white p-5" aria-label="Report">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-teal-700">Report</p>
          <h3 className="mt-1 text-xl font-semibold leading-snug text-zinc-950">{report.title}</h3>
        </div>
        <div className="shrink-0 rounded-md border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm font-semibold text-zinc-800">
          {Math.round(report.confidence * 100)}%
        </div>
      </div>

      {isLongForm ? <LongFormReport report={report} /> : <FlatReport report={report} />}
    </section>
  );
}

function FlatReport({ report }: { report: ResearchReport }) {
  return (
    <>
      <p className="text-sm leading-6 text-zinc-700">{report.summary}</p>
      <div className="mt-5 space-y-3">
        {report.key_findings.map((finding) => (
          <article key={finding.text} className="rounded-md border border-zinc-200 bg-zinc-50 px-4 py-3">
            <p className="text-sm font-medium leading-6 text-zinc-950">{finding.text}</p>
            <p className="mt-2 text-xs text-zinc-600">{finding.source_urls.join(", ")}</p>
          </article>
        ))}
      </div>
    </>
  );
}

function LongFormReport({ report }: { report: ResearchReport }) {
  const references = report.references ?? [];
  const refNumber = new Map<string, number>();
  references.forEach((reference, index) => refNumber.set(reference.url, index + 1));

  return (
    <article className="report-paper space-y-6">
      {report.abstract ? (
        <section>
          <h4 className="text-xs font-semibold uppercase tracking-[0.14em] text-zinc-500">Abstract</h4>
          <p className="mt-2 text-sm italic leading-7 text-zinc-700">{report.abstract}</p>
        </section>
      ) : null}

      {(report.sections ?? []).map((section, index) => (
        <section key={`${section.heading}-${index}`}>
          <h4 className="text-base font-semibold text-zinc-950">
            {index + 1}. {section.heading}
          </h4>
          <div className="mt-2 space-y-3">
            {section.paragraphs.map((paragraph, paragraphIndex) => (
              <p key={paragraphIndex} className="text-sm leading-7 text-zinc-800">
                {paragraph.text}
                <Citations paragraph={paragraph} refNumber={refNumber} />
              </p>
            ))}
          </div>
        </section>
      ))}

      {report.conclusion ? (
        <section>
          <h4 className="text-base font-semibold text-zinc-950">Conclusion</h4>
          <p className="mt-2 text-sm leading-7 text-zinc-800">{report.conclusion}</p>
        </section>
      ) : null}

      {references.length ? (
        <section>
          <h4 className="text-xs font-semibold uppercase tracking-[0.14em] text-zinc-500">References</h4>
          <ol className="mt-2 space-y-1.5">
            {references.map((reference, index) => (
              <ReferenceRow key={reference.url} reference={reference} index={index + 1} />
            ))}
          </ol>
        </section>
      ) : null}
    </article>
  );
}

function Citations({
  paragraph,
  refNumber,
}: {
  paragraph: ReportParagraph;
  refNumber: Map<string, number>;
}) {
  const numbers = paragraph.citations
    .map((url) => refNumber.get(url))
    .filter((value): value is number => typeof value === "number")
    .sort((a, b) => a - b);

  if (!numbers.length) {
    return null;
  }

  return (
    <sup className="ml-0.5 text-[0.65rem] font-medium text-teal-700">
      [{numbers.join(",")}]
    </sup>
  );
}

function ReferenceRow({ reference, index }: { reference: Reference; index: number }) {
  return (
    <li className="flex gap-2 text-xs leading-5 text-zinc-600">
      <span className="font-medium text-zinc-500">[{index}]</span>
      <span className="min-w-0">
        <span className="font-medium text-zinc-800">{reference.title}</span>{" "}
        <a href={reference.url} target="_blank" rel="noopener noreferrer" className="break-all text-teal-700 hover:underline">
          {reference.url}
        </a>
        <span className="ml-1 text-zinc-400">· credibility {Math.round(reference.credibility_score * 100)}%</span>
      </span>
    </li>
  );
}
