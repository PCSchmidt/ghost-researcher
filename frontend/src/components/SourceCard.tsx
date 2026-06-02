import { ExternalLink, ShieldCheck } from "lucide-react";

export function SourceCard({ url, toolResults }: { url: string; toolResults: Record<string, unknown>[] }) {
  const credibility = findCredibility(url, toolResults);

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
        {credibility === null ? "Credibility pending" : `Credibility ${Math.round(credibility * 100)}%`}
      </div>
    </article>
  );
}

function findCredibility(url: string, toolResults: Record<string, unknown>[]): number | null {
  for (const result of toolResults) {
    if (result.url === url && typeof result.score === "number") {
      return result.score;
    }
  }
  return null;
}