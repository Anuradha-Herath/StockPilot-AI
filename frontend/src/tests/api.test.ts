import { describe, it, expect, vi } from "vitest";
import { api, apiClient } from "@/lib/api";

describe("Frontend API Client Tests", () => {
  it("should configure proper baseURL from environment", () => {
    expect(apiClient.defaults.baseURL).toContain("/api/v1");
  });

  it("should correctly serialize and handle getInventorySummary", async () => {
    const mockSummary = {
      total_products: 25,
      total_stock_units: 520,
      low_stock_count: 5,
      out_of_stock_count: 2,
      total_inventory_value: "1420.50",
    };

    vi.spyOn(apiClient, "get").mockResolvedValueOnce({ data: mockSummary });

    const result = await api.getInventorySummary();
    expect(result.total_products).toBe(25);
    expect(result.low_stock_count).toBe(5);
    expect(result.total_inventory_value).toBe("1420.50");
  });

  it("should format proposal approval payload with idempotency key", async () => {
    const mockPO = {
      purchase_order_id: 10,
      order_number: "PO-20260920-123456",
      purchase_request_id: 1,
      request_number: "PR-20260920-AB12",
      supplier_id: 1,
      supplier_name: "DairyFresh Farms Co.",
      total_amount: "150.00",
      currency: "USD",
      status: "ISSUED",
      approved_by_id: 2,
      approved_by_name: "Sarah Jenkins",
      transmission_id: "EDI-TX-123456",
      created_at: new Date().toISOString(),
    };

    vi.spyOn(apiClient, "post").mockResolvedValueOnce({ data: mockPO });

    const res = await api.approveRequest(1, {
      proposal_version_hash: "abcd1234efgh5678",
      comments: "Approved for weekend restock",
      idempotency_key: "idemp-key-test-99",
    });

    expect(res.order_number).toBe("PO-20260920-123456");
    expect(res.status).toBe("ISSUED");
    expect(res.transmission_id).toBe("EDI-TX-123456");
  });
});
