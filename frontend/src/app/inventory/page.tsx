"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  Filter,
  Layers,
  MapPin,
  Package,
  Plus,
  RefreshCw,
  Search,
  SlidersHorizontal,
} from "lucide-react";
import { api } from "@/lib/api";
import { InventoryLevel, Product, StockStatus } from "@/lib/types";
import { StatusBadge } from "@/components/common/StatusBadge";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { EmptyState } from "@/components/common/EmptyState";
import { Modal } from "@/components/common/Modal";

export default function InventoryPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("ALL");
  const [selectedStatus, setSelectedStatus] = useState<string>("ALL");
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);

  // Stock Adjustment State
  const [adjustModalOpen, setAdjustModalOpen] = useState(false);
  const [adjustmentQty, setAdjustmentQty] = useState<number>(0);
  const [adjustmentReason, setAdjustmentReason] = useState("");
  const [adjustSubmitting, setAdjustSubmitting] = useState(false);
  const [adjustSuccessMsg, setAdjustSuccessMsg] = useState("");

  const fetchInventory = async () => {
    try {
      setLoading(true);
      const res = await api.getProducts({ size: 100 });
      setProducts(res.items || []);
    } catch (err) {
      console.error("Failed to load inventory", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInventory();
  }, []);

  // Filter products by search, category, and status
  const filteredProducts = (products || []).filter((p) => {
    if (!p) return false;
    const name = (p.name || "").toLowerCase();
    const sku = (p.sku || "").toLowerCase();
    const category = (p.category || "").toLowerCase();
    const q = (searchQuery || "").toLowerCase();

    const matchesSearch =
      !q || name.includes(q) || sku.includes(q) || category.includes(q);

    const matchesCategory =
      selectedCategory === "ALL" ||
      (p.category || "").toUpperCase() === selectedCategory.toUpperCase();

    const matchesStatus =
      selectedStatus === "ALL" ||
      (p.inventory && p.inventory.stock_status === selectedStatus);

    return matchesSearch && matchesCategory && matchesStatus;
  });

  const categories = [
    "ALL",
    ...Array.from(
      new Set(
        (products || [])
          .map((p) => p?.category)
          .filter((c): c is string => Boolean(c))
      )
    ),
  ];

  const handleOpenAdjust = (p: Product) => {
    setSelectedProduct(p);
    setAdjustmentQty(0);
    setAdjustmentReason("Physical count cycle adjustment");
    setAdjustSuccessMsg("");
    setAdjustModalOpen(true);
  };

  const handleExecuteAdjustment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProduct || adjustmentQty === 0) return;

    try {
      setAdjustSubmitting(true);
      await api.adjustStock({
        product_id: selectedProduct.id,
        adjustment_quantity: adjustmentQty,
        reason: adjustmentReason,
      });
      setAdjustSuccessMsg("Stock level successfully adjusted!");
      await fetchInventory();
      setTimeout(() => {
        setAdjustModalOpen(false);
      }, 1200);
    } catch (err: any) {
      alert(err.response?.data?.error?.message || "Failed to adjust stock level");
    } finally {
      setAdjustSubmitting(false);
    }
  };

  const formatCurrency = (val: number | string | null | undefined) => {
    if (val === null || val === undefined) return "$0.00";
    const num = typeof val === "string" ? parseFloat(val) : val;
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(isNaN(num) ? 0 : num);
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">
            Inventory & Catalog Management
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Monitor real-time warehouse stock, safety reorder thresholds, and bin locations.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={fetchInventory}
            className="flex items-center space-x-2 px-3 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 text-sm font-medium border border-slate-800 transition"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Refresh</span>
          </button>
          <Link
            href="/assistant?prompt=Show%20all%20products%20running%20low%20on%20stock"
            className="flex items-center space-x-2 px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold shadow-md shadow-blue-500/20 transition"
          >
            <Bot className="w-4 h-4" />
            <span>Audit Low Stock</span>
          </Link>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-4 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center gap-3">
          {/* Search Box */}
          <div className="relative flex-1">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search by product name, SKU, or category..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 placeholder-slate-500 text-sm focus:outline-none focus:border-blue-500 transition"
            />
          </div>

          {/* Stock Status Dropdown */}
          <div className="flex items-center space-x-2">
            <SlidersHorizontal className="w-4 h-4 text-slate-400" />
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="py-2.5 px-3 rounded-xl bg-slate-950 border border-slate-800 text-slate-200 text-sm focus:outline-none focus:border-blue-500"
            >
              <option value="ALL">All Stock Statuses</option>
              <option value="HEALTHY">Healthy Stock</option>
              <option value="LOW_STOCK">Low Stock (At/Below Reorder)</option>
              <option value="OUT_OF_STOCK">Out of Stock (Zero)</option>
            </select>
          </div>
        </div>

        {/* Category Pills */}
        <div className="flex items-center space-x-2 overflow-x-auto pb-1">
          <span className="text-xs font-semibold text-slate-400 uppercase mr-1">
            Category:
          </span>
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`px-3 py-1 rounded-lg text-xs font-medium whitespace-nowrap transition ${
                selectedCategory === cat
                  ? "bg-blue-600 text-white font-semibold shadow-sm"
                  : "bg-slate-950 text-slate-400 hover:text-slate-200 border border-slate-800"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Inventory Table */}
      {loading ? (
        <LoadingSpinner message="Fetching live catalog from database..." />
      ) : filteredProducts.length === 0 ? (
        <EmptyState
          title="No products matched your filters"
          description="Try broadening your search query or selecting 'All' categories."
          action={
            <button
              onClick={() => {
                setSearchQuery("");
                setSelectedCategory("ALL");
                setSelectedStatus("ALL");
              }}
              className="px-4 py-2 rounded-xl bg-slate-800 text-slate-200 text-xs font-medium hover:bg-slate-700"
            >
              Clear All Filters
            </button>
          }
        />
      ) : (
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-950/60 text-slate-400 font-semibold uppercase">
                  <th className="py-3 px-4">SKU & Name</th>
                  <th className="py-3 px-4">Category</th>
                  <th className="py-3 px-4">Stock Level</th>
                  <th className="py-3 px-4">Reorder Pt</th>
                  <th className="py-3 px-4">Location</th>
                  <th className="py-3 px-4">Unit Price</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {filteredProducts.map((p) => {
                  const inv = p.inventory;
                  const stockPercent = inv
                    ? Math.min(
                        100,
                        Math.round((inv.current_stock / (inv.max_stock || 100)) * 100)
                      )
                    : 0;

                  return (
                    <tr key={p.id} className="hover:bg-slate-800/40 transition">
                      <td className="py-3.5 px-4">
                        <div className="font-semibold text-slate-100">{p.name}</div>
                        <div className="text-[10px] text-slate-500 font-mono">
                          {p.sku} • {p.unit}
                        </div>
                      </td>
                      <td className="py-3.5 px-4 text-slate-300">{p.category}</td>
                      <td className="py-3.5 px-4 min-w-[140px]">
                        <div className="flex items-center justify-between text-[11px] mb-1">
                          <span
                            className={`font-bold ${
                              inv?.stock_status === "OUT_OF_STOCK"
                                ? "text-rose-400"
                                : inv?.stock_status === "LOW_STOCK"
                                ? "text-amber-400"
                                : "text-emerald-400"
                            }`}
                          >
                            {inv?.current_stock ?? 0} units
                          </span>
                          <span className="text-slate-500">
                            max {inv?.max_stock || 100}
                          </span>
                        </div>
                        <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              inv?.stock_status === "OUT_OF_STOCK"
                                ? "bg-rose-500"
                                : inv?.stock_status === "LOW_STOCK"
                                ? "bg-amber-500"
                                : "bg-emerald-500"
                            }`}
                            style={{ width: `${stockPercent}%` }}
                          />
                        </div>
                      </td>
                      <td className="py-3.5 px-4 font-mono text-slate-300">
                        {inv?.reorder_point ?? "-"}
                      </td>
                      <td className="py-3.5 px-4">
                        <span className="inline-flex items-center space-x-1 text-slate-400 font-mono text-[11px]">
                          <MapPin className="w-3 h-3 text-slate-500" />
                          <span>{inv?.warehouse_location || "N/A"}</span>
                        </span>
                      </td>
                      <td className="py-3.5 px-4 font-semibold text-slate-200">
                        {formatCurrency(p.unit_price)}
                      </td>
                      <td className="py-3.5 px-4">
                        {inv ? (
                          <StatusBadge status={inv.stock_status} />
                        ) : (
                          <span className="text-slate-500">Unassigned</span>
                        )}
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <div className="flex items-center justify-end space-x-2">
                          <button
                            onClick={() => handleOpenAdjust(p)}
                            className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium border border-slate-700 transition"
                          >
                            Adjust Stock
                          </button>
                          <Link
                            href={`/assistant?prompt=${encodeURIComponent(
                              `Show inventory details and supplier options for SKU ${p.sku}`
                            )}`}
                            className="p-1 rounded-lg bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 border border-blue-500/30 transition"
                            title="Ask AI Copilot"
                          >
                            <Bot className="w-4 h-4" />
                          </Link>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Manual Stock Adjustment Modal */}
      <Modal
        isOpen={adjustModalOpen}
        onClose={() => setAdjustModalOpen(false)}
        title={`Adjust Stock — ${selectedProduct?.name}`}
      >
        {adjustSuccessMsg ? (
          <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-center text-emerald-400 text-sm space-y-1">
            <CheckCircle2 className="w-6 h-6 mx-auto" />
            <p className="font-semibold">{adjustSuccessMsg}</p>
          </div>
        ) : (
          <form onSubmit={handleExecuteAdjustment} className="space-y-4 text-xs">
            <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-1">
              <p className="text-slate-400">
                Current Stock:{" "}
                <span className="font-bold text-slate-100">
                  {selectedProduct?.inventory?.current_stock ?? 0} {selectedProduct?.unit || "units"}
                </span>
              </p>
              <p className="text-slate-400">
                Safety Reorder Point:{" "}
                <span className="font-bold text-slate-100">
                  {selectedProduct?.inventory?.reorder_point ?? 0} {selectedProduct?.unit || "units"}
                </span>
              </p>
            </div>

            <div>
              <label className="block text-slate-300 font-semibold mb-1">
                Stock Adjustment Delta (+ to add, - to subtract)
              </label>
              <input
                type="number"
                required
                value={adjustmentQty}
                onChange={(e) => setAdjustmentQty(parseInt(e.target.value) || 0)}
                className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 text-sm focus:outline-none focus:border-blue-500"
                placeholder="e.g. 10 or -5"
              />
              <p className="text-[11px] text-slate-500 mt-1">
                New resulting stock:{" "}
                <span className="font-bold text-blue-400">
                  {(selectedProduct?.inventory?.current_stock || 0) + adjustmentQty}
                </span>
              </p>
            </div>

            <div>
              <label className="block text-slate-300 font-semibold mb-1">
                Reason for Adjustment
              </label>
              <input
                type="text"
                required
                value={adjustmentReason}
                onChange={(e) => setAdjustmentReason(e.target.value)}
                className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 text-sm focus:outline-none focus:border-blue-500"
                placeholder="e.g. Physical stock take recount"
              />
            </div>

            <div className="flex items-center justify-end space-x-3 pt-3 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setAdjustModalOpen(false)}
                className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 hover:bg-slate-700 text-xs font-semibold"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={adjustSubmitting || adjustmentQty === 0}
                className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold disabled:opacity-50 transition"
              >
                {adjustSubmitting ? "Applying..." : "Save Adjustment"}
              </button>
            </div>
          </form>
        )}
      </Modal>
    </div>
  );
}
