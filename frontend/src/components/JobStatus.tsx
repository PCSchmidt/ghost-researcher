"use client";

import { useEffect, useMemo, useState } from "react";
import { CheckCircle2, CircleDot, Radio, XCircle } from "lucide-react";
import { statusEventsUrl, type StatusEvent } from "@/lib/api";

const EVENT_TYPES = [
  "job_started",
  "tool_started",
  "tool_completed",
  "planner_stopped",
  "synthesis_completed",
  "job_completed",
];

type JobStatusProps = {
  jobId: string | null;
  initialEvents: StatusEvent[];
};

export function JobStatus({ jobId, initialEvents }: JobStatusProps) {
  const [streamedEvents, setStreamedEvents] = useState<StatusEvent[]>([]);
  const [streamState, setStreamState] = useState("connecting");

  useEffect(() => {
    if (!jobId) {
      return;
    }

    const source = new EventSource(statusEventsUrl(jobId));
    source.onopen = () => setStreamState("connected");
    source.onerror = () => {
      setStreamState("replay complete");
      source.close();
    };

    function handleMessage(message: MessageEvent<string>) {
      const event = JSON.parse(message.data) as StatusEvent;
      setStreamedEvents((currentEvents) => upsertEvent(currentEvents, event));
    }

    for (const eventType of EVENT_TYPES) {
      source.addEventListener(eventType, handleMessage as EventListener);
    }

    return () => {
      for (const eventType of EVENT_TYPES) {
        source.removeEventListener(eventType, handleMessage as EventListener);
      }
      source.close();
    };
  }, [jobId]);

  const orderedEvents = useMemo(
    () => mergeEvents(initialEvents, streamedEvents).sort((left, right) => left.sequence - right.sequence),
    [initialEvents, streamedEvents],
  );
  const displayStreamState = jobId ? streamState : "idle";

  return (
    <section className="mt-6 border-t border-zinc-200 pt-5" aria-label="Status stream">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 className="text-sm font-semibold uppercase tracking-[0.12em] text-zinc-600">Status</h2>
        <div className="inline-flex items-center gap-1.5 rounded-md border border-zinc-200 bg-zinc-50 px-2 py-1 text-xs text-zinc-600">
          <Radio size={13} aria-hidden="true" />
          {displayStreamState}
        </div>
      </div>
      <ol className="space-y-2">
        {orderedEvents.length ? (
          orderedEvents.map((event) => <StatusRow key={event.sequence} event={event} />)
        ) : (
          <li className="rounded-md border border-dashed border-zinc-300 bg-zinc-50 px-3 py-4 text-sm text-zinc-600">
            Status events will stream after a job is submitted.
          </li>
        )}
      </ol>
    </section>
  );
}

function StatusRow({ event }: { event: StatusEvent }) {
  const isComplete = event.status === "completed" || event.event_type === "job_completed";
  const isStopped = event.status === "stopped";
  const Icon = isStopped ? XCircle : isComplete ? CheckCircle2 : CircleDot;

  return (
    <li className="rounded-md border border-zinc-200 bg-white px-3 py-3">
      <div className="flex items-start gap-3">
        <Icon size={17} className={isStopped ? "mt-0.5 text-amber-700" : isComplete ? "mt-0.5 text-teal-700" : "mt-0.5 text-zinc-500"} aria-hidden="true" />
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2">
            <p className="truncate text-sm font-medium text-zinc-950">{event.message}</p>
            <span className="text-xs text-zinc-500">#{event.sequence}</span>
          </div>
          {event.tool_name ? <p className="mt-1 text-xs text-zinc-600">{event.tool_name}</p> : null}
        </div>
      </div>
    </li>
  );
}

function upsertEvent(events: StatusEvent[], event: StatusEvent): StatusEvent[] {
  if (events.some((currentEvent) => currentEvent.sequence === event.sequence)) {
    return events.map((currentEvent) => (currentEvent.sequence === event.sequence ? event : currentEvent));
  }
  return [...events, event];
}

function mergeEvents(initialEvents: StatusEvent[], streamedEvents: StatusEvent[]): StatusEvent[] {
  return streamedEvents.reduce(upsertEvent, initialEvents);
}