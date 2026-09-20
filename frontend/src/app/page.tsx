"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowRight,
  Bot,
  Boxes,
  CheckCircle,
  DollarSign,
  PackageX,
  RefreshCw,
  ShieldCheck,
  ShoppingCart,
  TrendingDown,
} from "lucide-react";
import { api } from "@/lib/api";
import {
  AuditLog,
  InventoryLevel,
  InventorySummary,
  PendingApprovalSummary,
  Product,
  PurchaseOrder,
} from "@/lib/types";
import { MetricCard } from "@/components/common/MetricCard";
import { StatusBadge } from "@/components/common/StatusBadge";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { useUser } from "@/context/UserContext";

export default function DashboardPage() {
  const { currentUser } = useUser();
  const [summary, setSummary] = useState<InventorySummary | null>(null);
  const [lowStockProducts, setLowStockProducts] = useState<Product[]>([]);
  const [pendingApprovals, setPendingApprovals] = useState<PendingApprovalSummary[]>([]);
  const [recentOrders, setRecentOrders] = useState<PurchaseOrder[]>([]);
  const [recentAudit, setRecentAudit] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchDashboardData = async () => {
    try {
      setRefreshing(true);
      const [sumRes, invRes, ordersRes, auditRes] = await Promise.all([
        api.getInventorySummary(),
        api.getProducts({ size: 100 }),
        api.getPurchaseOrders({ size: 5 }),
        api.getAuditLogs({ size: 6 }),
      ]);

      setSummary(sumRes);
      setRecentOrders(ordersRes.items || []);
      setRecentAudit(auditRes.items || []);

      // Filter products that have low or out of stock status
      const lowItems = invRes.items.filter(
        (p) =>
          p.inventory &&
          (p.inventory.stock_status === "LOW_STOCK" ||
            p.inventory.stock_status === "OUT_OF_STOCK")
      );
      setLowStockProducts(lowItems);

      // Attempt to load pending approvals (allowed for Manager/Admin)
      try {
        const approvals = await api.getPendingApprovals();
        setPendingApprovals(approvals);
      } catch {
        // Operator gets 403, which is expected by RBAC design
        setPendingApprovals([]);
      }
    } catch (err) {
      console.error("Failed to load dashboard data", err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, [currentUser]);

  if (loading) {
    return <LoadingSpinner message="Connecting to StockPilot engine..." size="lg" />;
  }

  const formatCurrency = (amount: number | string) => {
    const num = typeof amount === "string" ? parseFloat(amount) : amount;
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(num || 0);
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 p-6 rounded-2xl bg-gradient-to-r from-slate-900 via-slate-900/90 to-blue-950/40 border border-slate-800">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-2xl font-bold text-slate-100">
              Welcome back, {currentUser.full_name.split(" ")[0]}
            </h1>
            <span className="px-2 py-0.5 rounded text-xs font-semibold bg-blue-500/20 text-blue-300 border border-blue-500/30">
              {currentUser.role}
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Real-time inventory intelligence and human-in-the-loop procurement status.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={fetchDashboardData}
            disabled={refreshing}
            className="flex items-center space-x-2 px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium transition border border-slate-700 disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin text-blue-400" : ""}`} />
            <span>{refreshing ? "Syncing..." : "Refresh"}</span>
          </button>
          <Link
            href="/assistant"
            className="flex items-center space-x-2 px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold shadow-lg shadow-blue-500/20 transition"
          >
            <Bot className="w-4 h-4" />
            <span>Open AI Copilot</span>
          </Link>
        </div>
      </div>

      {/* KPI Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <MetricCard
          title="Catalog Products"
          value={summary?.total_products || 0}
          subtitle={`${summary?.total_stock_units || 0} units on hand`}
          icon={Boxes}
          color="blue"
        />
        <MetricCard
          title="Low Stock Alerts"
          value={summary?.low_stock_count || 0}
          subtitle="At or below reorder pt"
          icon={AlertTriangle}
          color="amber"
        />
        <MetricCard
          title="Out of Stock"
          value={summary?.out_of_stock_count || 0}
          subtitle="Critical shortages"
          icon={PackageX}
          color="rose"
        />
        <MetricCard
          title="Pending Approvals"
          value={pendingApprovals.length}
          subtitle="Awaiting manager review"
          icon={ShieldCheck}
          color="indigo"
        />
        <MetricCard
          title="Inventory Valuation"
          value={formatCurrency(summary?.total_inventory_value || 0)}
          subtitle="Calculated at retail value"
          icon={DollarSign}
          color="emerald"
        />
      </div>

      {/* Two Column Section: Low Stock Items & Recent Orders */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Low Stock Attention List (2 columns wide) */}
        <div className="lg:col-span-2 bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-2">
              <TrendingDown className="w-5 h-5 text-amber-400" />
              <h2 className="text-lg font-bold text-slate-100">
                Replenishment Priority Alerts
              </h2>
            </div>
            <Link
              href="/inventory"
              className="text-xs font-semibold text-blue-400 hover:text-blue-300 flex items-center space-x-1"
            >
              <span>View All Inventory</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          {lowStockProducts.length === 0 ? (
            <div className="flex flex-col items-center justify-center p-8 text-center bg-slate-950/40 rounded-xl border border-slate-800/60">
              <CheckCircle className="w-8 h-8 text-emerald-400 mb-2" />
              <p className="text-sm font-medium text-slate-200">
                All inventory levels healthy!
              </p>
              <p className="text-xs text-slate-400">
                No products are currently below their safety reorder thresholds.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400 font-semibold uppercase">
                    <th className="py-2.5 px-3">Product</th>
                    <th className="py-2.5 px-3">Category</th>
                    <th className="py-2.5 px-3">Stock / Reorder</th>
                    <th className="py-2.5 px-3">Status</th>
                    <th className="py-2.5 px-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {lowStockProducts.slice(0, 5).map((p) => {
                    const inv = p.inventory!;
                    return (
                      <tr key={p.id} className="hover:bg-slate-800/40 transition">
                        <td className="py-3 px-3">
                          <p className="font-semibold text-slate-100">{p.name}</p>
                          <p className="text-[10px] text-slate-500 font-mono">{p.sku}</p>
                        </td>
                        <td className="py-3 px-3 text-slate-300">{p.category}</td>
                        <td className="py-3 px-3">
                          <span className="font-bold text-amber-400">
                            {inv.current_stock}
                          </span>
                          <span className="text-slate-500"> / {inv.reorder_point}</span>
                        </td>
                        <td className="py-3 px-3">
                          <StatusBadge status={inv.stock_status} />
                        </td>
                        <td className="py-3 px-3 text-right">
                          <Link
                            href={`/assistant?prompt=${encodeURIComponent(
                              `Calculate replenishment proposal for ${p.name} (${p.sku})`
                            )}`}
                            className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-blue-600/20 text-blue-400 hover:bg-blue-600/30 border border-blue-500/30 text-xs font-medium transition"
                          >
                            <span>Draft Restock</span>
                            <ArrowRight className="w-3 h-3" />
                          </Link>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Recent Audit & System Ledger (1 column wide) */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-slate-100">Live Activity Feed</h2>
              <Link
                href="/audit"
                className="text-xs font-semibold text-blue-400 hover:text-blue-300 flex items-center space-x-1"
              >
                <span>Full Ledger</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            <div className="space-y-3">
              {recentAudit.length === 0 ? (
                <p className="text-xs text-slate-500">No activity recorded yet.</p>
              ) : (
                recentAudit.map((log) => (
                  <div
                    key={log.id}
                    className="p-3 rounded-xl bg-slate-950/50 border border-slate-800/80 text-xs"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-slate-200">
                        {log.action.replace(/_/g, " ")}
                      </span>
                      <span
                        className={`text-[10px] font-bold px-1.5 py-0.2 rounded ${
                          log.actor_type === "AI_AGENT"
                            ? "bg-blue-500/20 text-blue-400"
                            : log.actor_type === "USER"
                            ? "bg-purple-500/20 text-purple-400"
                            : "bg-slate-500/20 text-slate-400"
                        }`}
                      >
                        {log.actor_type}
                      </span>
                    </div>
                    <p className="text-slate-400 mt-1 line-clamp-1">
                      {log.description || `${log.entity_type} ID ${log.entity_id}`}
                    </p>
                    <p className="text-[10px] text-slate-500 mt-1">
                      {new Date(log.timestamp).toLocaleTimeString()} •{" "}
                      {new Date(log.timestamp).toLocaleDateString()}
                    </p>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="mt-4 pt-4 border-t border-slate-800">
            <Link
              href="/approvals"
              className="w-full flex items-center justify-center space-x-2 py-2.5 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 text-white text-xs font-semibold hover:opacity-95 transition shadow-md"
            >
              <ShieldCheck className="w-4 h-4" />
              <span>Review Pending Approvals ({pendingApprovals.length})</span>
            </Link>
          </div>
        </div>
      </div>

      {/* Recent Issued Purchase Orders */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <ShoppingCart className="w-5 h-5 text-indigo-400" />
            <h2 className="text-lg font-bold text-slate-100">
              Recent Procurement Orders
            </h2>
          </div>
          <Link
            href="/approvals"
            className="text-xs font-semibold text-blue-400 hover:text-blue-300 flex items-center space-x-1"
          >
            <span>View All in Approvals Hub</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {recentOrders.length === 0 ? (
          <div className="p-8 text-center text-slate-500 text-xs">
            No purchase orders issued yet. Create and approve proposals to dispatch orders.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 font-semibold uppercase">
                  <th className="py-2.5 px-3">Order Number</th>
                  <th className="py-2.5 px-3">Supplier</th>
                  <th className="py-2.5 px-3">Items</th>
                  <th className="py-2.5 px-3">Total Amount</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Issued Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {recentOrders.map((po) => (
                  <tr key={po.id} className="hover:bg-slate-800/40 transition">
                    <td className="py-3 px-3 font-mono font-semibold text-blue-400">
                      {po.order_number}
                    </td>
                    <td className="py-3 px-3 text-slate-200 font-medium">
                      {po.supplier_name || `Supplier ID ${po.supplier_id}`}
                    </td>
                    <td className="py-3 px-3 text-slate-300">
                      {po.items.length} line item(s)
                    </td>
                    <td className="py-3 px-3 font-semibold text-slate-100">
                      {formatCurrency(po.total_amount)}
                    </td>
                    <td className="py-3 px-3">
                      <StatusBadge status={po.status} type="order" />
                    </td>
                    <td className="py-3 px-3 text-slate-400">
                      {new Date(po.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
