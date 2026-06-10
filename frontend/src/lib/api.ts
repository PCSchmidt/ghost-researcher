export type ToolCall = {
  name: string;
  arguments: Record<string, unknown>;
};

export type PlannerDecision = {
  tool_call: ToolCall | null;
  termination_reason: string | null;
  should_stop: boolean;
};

export type StatusEvent = {
  sequence: number;
  event_type: string;
  status: string;
  message: string;
  tool_name: string | null;
  payload: Record<string, unknown>;
};

export type EvidenceRecord = {
  url: string;
  title: string;
  claims_count: number;
  credibility_score: number;
  evidence_type?: string;
};

export type EvidenceQuality = {
  sources_visited_count: number;
  assessed_evidence_count: number;
  extracted_evidence_count: number;
  navigation_fallback_evidence_count: number;
  average_assessed_credibility: number;
  detection_event_count: number;
};

export type SessionState = {
  research_goal: string;
  steps_taken: number;
  planner_turns: number;
  running_tokens: number;
  running_cost_usd: number;
  sources_visited: string[];
  current_source_url: string | null;
  search_queries: string[];
  source_candidates: string[];
  termination_state: string;
  termination_reason: string | null;
  evidence_quality: EvidenceQuality;
  evidence_records: EvidenceRecord[];
};

export type ReportClaim = {
  text: string;
  source_urls: string[];
};

export type ResearchReport = {
  title: string;
  summary: string;
  key_findings: ReportClaim[];
  sources_used: string[];
  confidence: number;
};

export type ResearchJob = {
  job_id: string;
  created_at: string;
  updated_at: string;
  status: string;
  error?: string | null;
  status_events: StatusEvent[];
  session: SessionState;
  decisions: PlannerDecision[];
  tool_results: Record<string, unknown>[];
  synthesis: ResearchReport | null;
};

export function isTerminalStatus(status: string): boolean {
  return status !== "running";
}

export function apiBaseUrl(): string {
  return (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");
}

export function statusEventsUrl(jobId: string): string {
  return `${apiBaseUrl()}/research/${encodeURIComponent(jobId)}/events`;
}

export async function submitResearchGoal(researchGoal: string): Promise<ResearchJob> {
  const response = await fetch(`${apiBaseUrl()}/research`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ research_goal: researchGoal }),
  });

  if (!response.ok) {
    const detail = await readErrorDetail(response);
    throw new Error(
      detail
        ? `Research request failed (status ${response.status}): ${detail}`
        : `Research request failed with status ${response.status}`,
    );
  }

  return response.json() as Promise<ResearchJob>;
}

export async function getResearchJob(jobId: string): Promise<ResearchJob> {
  const response = await fetch(`${apiBaseUrl()}/research/${encodeURIComponent(jobId)}`);

  if (!response.ok) {
    const detail = await readErrorDetail(response);
    throw new Error(
      detail
        ? `Failed to load job (status ${response.status}): ${detail}`
        : `Failed to load job with status ${response.status}`,
    );
  }

  return response.json() as Promise<ResearchJob>;
}

async function readErrorDetail(response: Response): Promise<string | null> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string" && body.detail.trim()) {
      return body.detail.trim();
    }
  } catch {
    // body was not JSON (e.g. an edge-proxy timeout page); fall back to status only
  }
  return null;
}
