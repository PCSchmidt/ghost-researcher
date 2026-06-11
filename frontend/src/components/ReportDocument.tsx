import type { Reference, ReportParagraph, ResearchReport } from "@/lib/api";

/**
 * Print/permalink layout that renders a report as an academic paper.
 * Distinct from ReportViewer (the in-app card): this is the shareable, print-to-PDF
 * document. Pairs with the `@media print` rules in globals.css.
 */
export function ReportDocument({ report, meta }: { report: ResearchReport; meta?: string }) {
  const isLongForm = Boolean(report.sections && report.sections.length > 0);
  const references = report.references ?? [];
  const refNumber = new Map<string, number>();
  references.forEach((reference, index) => refNumber.set(reference.url, index + 1));

  return (
    <article className="report-paper mx-auto max-w-[760px] px-6 py-10 text-zinc-900">
      <header className="mb-8 text-center">
        <h1 className="text-balance text-3xl font-semibold leading-tight tracking-tight">{report.title}</h1>
        {meta ? <p className="report-meta mt-3 text-xs uppercase tracking-[0.16em] text-zinc-500">{meta}</p> : null}
      </header>

      {report.abstract ? (
        <section className="mx-auto mb-8 max-w-[640px]">
          <h2 className="mb-2 text-center text-xs font-semibold uppercase tracking-[0.18em] text-zinc-500">Abstract</h2>
          <p className="text-[0.95rem] italic leading-7 text-zinc-700">{report.abstract}</p>
        </section>
      ) : null}

      {isLongForm ? (
        (report.sections ?? []).map((section, index) => (
          <section key={`${section.heading}-${index}`} className="mb-6 break-inside-avoid">
            <h2 className="mb-2 text-lg font-semibold tracking-tight">
              {index + 1}. {section.heading}
            </h2>
            <div className="space-y-3">
              {section.paragraphs.map((paragraph, paragraphIndex) => (
                <p key={paragraphIndex} className="text-justify text-[0.95rem] leading-7">
                  {paragraph.text}
                  <Citations paragraph={paragraph} refNumber={refNumber} />
                </p>
              ))}
            </div>
          </section>
        ))
      ) : (
        <section className="mb-6">
          <p className="text-justify text-[0.95rem] leading-7">{report.summary}</p>
          <ul className="mt-4 space-y-2">
            {report.key_findings.map((finding) => (
              <li key={finding.text} className="text-[0.95rem] leading-7">
                {finding.text}
              </li>
            ))}
          </ul>
        </section>
      )}

      {report.conclusion ? (
        <section className="mb-6 break-inside-avoid">
          <h2 className="mb-2 text-lg font-semibold tracking-tight">Conclusion</h2>
          <p className="text-justify text-[0.95rem] leading-7">{report.conclusion}</p>
        </section>
      ) : null}

      {references.length ? (
        <section className="mt-8 border-t border-zinc-200 pt-4">
          <h2 className="mb-3 text-xs font-semibold uppercase tracking-[0.18em] text-zinc-500">References</h2>
          <ol className="space-y-1.5">
            {references.map((reference, index) => (
              <ReferenceRow key={reference.url} reference={reference} index={index + 1} />
            ))}
          </ol>
        </section>
      ) : null}
    </article>
  );
}

function Citations({ paragraph, refNumber }: { paragraph: ReportParagraph; refNumber: Map<string, number> }) {
  const numbers = paragraph.citations
    .map((url) => refNumber.get(url))
    .filter((value): value is number => typeof value === "number")
    .sort((a, b) => a - b);

  if (!numbers.length) {
    return null;
  }
  return <sup className="ml-0.5 align-super text-[0.6rem] font-medium text-teal-700">[{numbers.join(",")}]</sup>;
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
