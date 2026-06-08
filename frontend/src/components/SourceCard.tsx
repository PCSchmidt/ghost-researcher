import { ExternalLink, ShieldCheck } from "lucide-react";
import type { EvidenceRecord } from "@/lib/api";

export function SourceCard({
  url,
  evidenceRecords,
  toolResults,
}: {
  url: string;
  evidenceRecords: EvidenceRecord[];
  toolResults: Record<string, unknown>[];
}) {
  const credibility = findCredibility(url, evidenceRecords, toolResults);

  return (
    <article className="rounded-md border border-zinc-200 bg-white p-4">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h4 className="truncate text-sm font-semibold text-zinc-950">{new URL(url).hostname}</h4>
          <p className="mt-1 break-all text-xs leading-5 text-zinc-600">{url}</p>
        </div>
        <a className="text-zinc-500 transition hover:text-teal-700" href={url} target="_blank" rel="noreferrer" aria-label={`Open ${url}`}>
          <ExternalLink size={16} aria-hidden="true" />
        </a>
      </div>
      <div className="inline-flex items-center gap-2 rounded-md bg-zinc-50 px-2 py-1 text-xs font-medium text-zinc-700">
        <ShieldCheck size={14} className="text-teal-700" aria-hidden="true" />
        {credibility === null
          ? "Credibility pending"
          : `${credibility.label} ${Math.round(credibility.score * 100)}%`}
      </div>
    </article>
  );
}

function findCredibility(
  url: string,
  evidenceRecords: EvidenceRecord[],
  toolResults: Record<string, unknown>[],
): { score: number; label: string } | null {
  const evidence = findBestEvidence(url, evidenceRecords);
  if (evidence) {
    return {
      score: evidence.credibility_score,
      label: evidence.evidence_type === "assessed" ? "Credibility" : evidenceLabel(evidence.evidence_type),
    };
  }

  for (const result of toolResults) {
    if (result.url === url && typeof result.score === "number") {
      return { score: result.score, label: "Credibility" };
    }
  }
  return null;
}

function findBestEvidence(url: string, evidenceRecords: EvidenceRecord[]): EvidenceRecord | null {
  const matches = evidenceRecords.filter((record) => record.url === url);
  return (
    matches.find((record) => record.evidence_type === "assessed") ??
    matches.find((record) => record.evidence_type === "extracted") ??
    matches.find((record) => record.evidence_type === "navigation_fallback") ??
    matches[0] ??
    null
  );
}

function evidenceLabel(evidenceType?: string): string {
  if (evidenceType === "extracted") {
    return "Extracted";
  }
  if (evidenceType === "navigation_fallback") {
    return "Fallback";
  }
  return "Credibility";
}
