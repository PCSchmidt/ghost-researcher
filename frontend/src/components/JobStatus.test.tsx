import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { JobStatus } from "@/components/JobStatus";
import type { StatusEvent } from "@/lib/api";

class MockEventSource {
  static instances: MockEventSource[] = [];
  onopen: (() => void) | null = null;
  onerror: (() => void) | null = null;
  listeners = new Map<string, EventListener>();

  constructor(public url: string) {
    MockEventSource.instances.push(this);
  }

  addEventListener(eventType: string, listener: EventListener) {
    this.listeners.set(eventType, listener);
  }

  removeEventListener(eventType: string) {
    this.listeners.delete(eventType);
  }

  close() {}
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("JobStatus", () => {
  it("renders initial status events in order", () => {
    const events: StatusEvent[] = [
      event(2, "tool_completed", "Completed web_search", "web_search"),
      event(0, "job_started", "Research job accepted", null),
    ];

    render(<JobStatus jobId={null} initialEvents={events} />);

    expect(screen.getByText("Research job accepted")).toBeInTheDocument();
    expect(screen.getByText("Completed web_search")).toBeInTheDocument();
    expect(screen.getByText("#0")).toBeInTheDocument();
    expect(screen.getByText("#2")).toBeInTheDocument();
  });

  it("opens an EventSource for the persisted event stream", () => {
    vi.stubGlobal("EventSource", MockEventSource);
    MockEventSource.instances = [];

    render(<JobStatus jobId="job-1" initialEvents={[]} />);

    expect(MockEventSource.instances[0].url).toBe("http://localhost:8000/research/job-1/events");
  });
});

function event(sequence: number, eventType: string, message: string, toolName: string | null): StatusEvent {
  return {
    sequence,
    event_type: eventType,
    status: "completed",
    message,
    tool_name: toolName,
    payload: {},
  };
}