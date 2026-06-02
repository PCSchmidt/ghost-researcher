"use client";

import { FormEvent, useState } from "react";
import { LoaderCircle, Send } from "lucide-react";

type ResearchFormProps = {
  isSubmitting: boolean;
  onSubmit: (researchGoal: string) => Promise<void>;
};

export function ResearchForm({ isSubmitting, onSubmit }: ResearchFormProps) {
  const [researchGoal, setResearchGoal] = useState("Find recent FAA BVLOS guidance and summarize credible sources");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedGoal = researchGoal.trim();
    if (!trimmedGoal || isSubmitting) {
      return;
    }
    await onSubmit(trimmedGoal);
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3" aria-label="Research request">
      <label htmlFor="research-goal" className="block text-sm font-medium text-zinc-800">
        Research goal
      </label>
      <textarea
        id="research-goal"
        value={researchGoal}
        onChange={(event) => setResearchGoal(event.target.value)}
        rows={6}
        className="w-full resize-none rounded-md border border-zinc-300 bg-white px-3 py-3 text-sm leading-6 text-zinc-950 outline-none transition focus:border-teal-700 focus:ring-2 focus:ring-teal-100"
      />
      <button
        type="submit"
        disabled={isSubmitting || !researchGoal.trim()}
        className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-md bg-zinc-950 px-4 text-sm font-semibold text-white transition hover:bg-zinc-800 disabled:cursor-not-allowed disabled:bg-zinc-300 disabled:text-zinc-600"
      >
        {isSubmitting ? <LoaderCircle size={17} className="animate-spin" aria-hidden="true" /> : <Send size={17} aria-hidden="true" />}
        {isSubmitting ? "Running" : "Run research"}
      </button>
    </form>
  );
}