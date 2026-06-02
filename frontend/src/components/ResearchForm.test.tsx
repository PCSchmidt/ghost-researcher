import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ResearchForm } from "@/components/ResearchForm";

describe("ResearchForm", () => {
  it("submits the entered research goal", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<ResearchForm isSubmitting={false} onSubmit={onSubmit} />);

    fireEvent.change(screen.getByLabelText("Research goal"), { target: { value: " Review NASA sources " } });
    fireEvent.click(screen.getByRole("button", { name: "Run research" }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledWith("Review NASA sources"));
  });

  it("disables submission while running", () => {
    render(<ResearchForm isSubmitting={true} onSubmit={vi.fn()} />);

    expect(screen.getByRole("button", { name: "Running" })).toBeDisabled();
  });
});