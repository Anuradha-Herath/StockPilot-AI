import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatusBadge } from "@/components/common/StatusBadge";
import { MetricCard } from "@/components/common/MetricCard";
import { EmptyState } from "@/components/common/EmptyState";
import { Boxes, ShieldCheck } from "lucide-react";

describe("Frontend Component Tests", () => {
  it("renders StatusBadge with correct text and styling for HEALTHY", () => {
    render(<StatusBadge status="HEALTHY" />);
    const badge = screen.getByText("HEALTHY");
    expect(badge).toBeDefined();
    expect(badge.className).toContain("text-emerald-400");
  });

  it("renders StatusBadge with correct styling for LOW_STOCK and PENDING_APPROVAL", () => {
    render(<StatusBadge status="LOW_STOCK" />);
    const lowStock = screen.getByText("LOW STOCK");
    expect(lowStock).toBeDefined();
    expect(lowStock.className).toContain("text-amber-400");

    render(<StatusBadge status="PENDING_APPROVAL" />);
    const pending = screen.getByText("PENDING APPROVAL");
    expect(pending).toBeDefined();
    expect(pending.className).toContain("text-amber-400");
  });

  it("renders MetricCard with title, value, and subtitle", () => {
    render(
      <MetricCard
        title="Total Stock"
        value={1500}
        subtitle="Across 25 SKUs"
        icon={Boxes}
        color="blue"
      />
    );
    expect(screen.getByText("Total Stock")).toBeDefined();
    expect(screen.getByText("1500")).toBeDefined();
    expect(screen.getByText("Across 25 SKUs")).toBeDefined();
  });

  it("renders EmptyState with custom title and description", () => {
    render(
      <EmptyState
        title="No Low Stock Items"
        description="All items are above their safety reorder thresholds."
        icon={ShieldCheck}
      />
    );
    expect(screen.getByText("No Low Stock Items")).toBeDefined();
    expect(screen.getByText("All items are above their safety reorder thresholds.")).toBeDefined();
  });
});
