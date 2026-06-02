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

export type SessionState = {
  research_goal: string;
  steps_taken: number;
  planner_turns: number;
  running_tokens: number;
  running_cost_usd: number;
  sources_visited: string[];
  search_queries: string[];
  source_candidates: string[];
  termination_state: string;
  termination_reason: string | null;
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
  status_events: StatusEvent[];
  session: SessionState;
  decisions: PlannerDecision[];
  tool_results: Record<string, unknown>[];
  synthesis: ResearchReport | null;
};

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
    throw new Error(`Research request failed with status ${response.status}`);
  }

  return response.json() as Promise<ResearchJob>;
}