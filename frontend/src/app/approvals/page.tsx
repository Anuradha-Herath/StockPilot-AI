"use client";

import React, { useEffect, useState } from "react";
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ExternalLink,
  FileCheck,
  Hash,
  History,
  Lock,
  RefreshCw,
  Send,
  ShieldAlert,
  ShieldCheck,
  Trash2,
  UserCheck,
  XCircle,
} from "lucide-react";
import { api } from "@/lib/api";
import {
  PendingApprovalSummary,
  PurchaseOrder,
  PurchaseRequest,
} from "@/lib/types";
import { useUser } from "@/context/UserContext";
import { StatusBadge } from "@/components/common/StatusBadge";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { EmptyState } from "@/components/common/EmptyState";
import { Modal } from "@/components/common/Modal";

export default function ApprovalsPage() {
  const { currentUser, isManagerOrAdmin } = useUser();
  const [activeTab, setActiveTab] = useState<"pending" | "orders">("pending");
  const [pendingApprovals, setPendingApprovals] = useState<PendingApprovalSummary[]>([]);
  const [purchaseOrders, setPurchaseOrders] = useState<PurchaseOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);

  // Modals state
  const [selectedProposal, setSelectedProposal] = useState<PendingApprovalSummary | null>(null);
  const [approveModalOpen, setApproveModalOpen] = useState(false);
  const [rejectModalOpen, setRejectModalOpen] = useState(false);
  const [approvalNotes, setApprovalNotes] = useState("");
  const [rejectionReason, setRejectionReason] = useState("");
  const [feedbackMsg, setFeedbackMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const fetchApprovalData = async () => {
    try {
      setLoading(true);
      setFeedbackMsg(null);

      // 1. Fetch Orders (always available)
      const ordersRes = await api.getPurchaseOrders({ size: 50 });
      setPurchaseOrders(ordersRes.items || []);

      // 2. Fetch Pending Approvals (Requires Manager/Admin)
      if (isManagerOrAdmin) {
        const pending = await api.getPendingApprovals();
        setPendingApprovals(pending || []);
      } else {
        setPendingApprovals([]);
      }
    } catch (err: any) {
      console.error("Error fetching approval data", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApprovalData();
  }, [currentUser, isManagerOrAdmin]);

  const handleOpenApprove = (proposal: PendingApprovalSummary) => {
    setSelectedProposal(proposal);
    setApprovalNotes(`Approved by ${currentUser.full_name} for procurement cycle.`);
    setApproveModalOpen(true);
  };

  const handleOpenReject = (proposal: PendingApprovalSummary) => {
    setSelectedProposal(proposal);
    setRejectionReason("");
    setRejectModalOpen(true);
  };

  const handleExecuteApprove = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProposal) return;

    try {
      setActionLoading(true);
      const idempotencyKey = `idemp_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;
      const result = await api.approveRequest(selectedProposal.request_id, {
        proposal_version_hash: selectedProposal.proposal_version_hash,
        comments: approvalNotes,
        idempotency_key: idempotencyKey,
      });

      setFeedbackMsg({
        type: "success",
        text: `Order ${result.order_number} successfully issued to ${result.supplier_name}! EDI Transmission ID: ${result.transmission_id}`,
      });
      setApproveModalOpen(false);
      await fetchApprovalData();
    } catch (err: any) {
      const msg = err.response?.data?.error?.message || "Failed to approve proposal";
      alert(`Approval Failed: ${msg}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleExecuteReject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProposal || !rejectionReason.trim()) return;

    try {
      setActionLoading(true);
      await api.rejectRequest(selectedProposal.request_id, {
        comments: rejectionReason,
      });

      setFeedbackMsg({
        type: "success",
        text: `Purchase Request ${selectedProposal.request_number} rejected.`,
      });
      setRejectModalOpen(false);
      await fetchApprovalData();
    } catch (err: any) {
      const msg = err.response?.data?.error?.message || "Failed to reject proposal";
      alert(`Rejection Failed: ${msg}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleExpireStale = async () => {
    if (!confirm("Expire unapproved draft proposals older than 24 hours?")) return;
    try {
      setActionLoading(true);
      const res = await api.expireStaleProposals(24);
      setFeedbackMsg({
        type: "success",
        text: res.message,
      });
      await fetchApprovalData();
    } catch (err: any) {
      alert(err.response?.data?.error?.message || "Failed to sweep stale proposals");
    } finally {
      setActionLoading(false);
    }
  };

  const formatCurrency = (val: number | string) => {
    const num = typeof val === "string" ? parseFloat(val) : val;
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(num || 0);
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-2xl font-bold text-slate-100">
              Procurement Approval Center
            </h1>
            <span className="px-2 py-0.5 rounded text-xs font-semibold bg-purple-500/20 text-purple-300 border border-purple-500/30">
              Human-in-the-Loop Gating
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Review AI-generated purchase proposals, verify SHA-256 version hashes, and authorize mock EDI purchase orders.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={fetchApprovalData}
            className="flex items-center space-x-2 px-3 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 text-sm font-medium border border-slate-800 transition"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Refresh</span>
          </button>

          {isManagerOrAdmin && (
            <button
              onClick={handleExpireStale}
              disabled={actionLoading}
              className="flex items-center space-x-2 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium border border-slate-700 transition"
              title="Expire unapproved requests older than 24h"
            >
              <Clock className="w-3.5 h-3.5 text-amber-400" />
              <span>Expire Stale</span>
            </button>
          )}
        </div>
      </div>

      {/* RBAC Warning Banner for Operators */}
      {!isManagerOrAdmin && (
        <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-start space-x-3 text-amber-300 text-xs">
          <Lock className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div>
            <p className="font-bold">Operator Mode (View Only)</p>
            <p className="text-amber-300/80 mt-0.5">
              You are signed in as an Inventory Operator. You can inspect purchase orders, but approval actions are restricted to **Manager** or **Admin** roles. Use the persona switcher in the top right navbar to test Manager approvals.
            </p>
          </div>
        </div>
      )}

      {/* Feedback Alert */}
      {feedbackMsg && (
        <div
          className={`p-4 rounded-2xl flex items-center space-x-3 text-xs ${
            feedbackMsg.type === "success"
              ? "bg-emerald-500/10 border border-emerald-500/30 text-emerald-300"
              : "bg-rose-500/10 border border-rose-500/30 text-rose-300"
          }`}
        >
          <CheckCircle2 className="w-5 h-5 shrink-0" />
          <span className="font-medium">{feedbackMsg.text}</span>
        </div>
      )}

      {/* Tabs */}
      <div className="flex items-center space-x-2 border-b border-slate-800 pb-2">
        <button
          onClick={() => setActiveTab("pending")}
          className={`flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-semibold transition ${
            activeTab === "pending"
              ? "bg-blue-600 text-white shadow-md shadow-blue-500/20"
              : "bg-slate-900 text-slate-400 hover:text-slate-200"
          }`}
        >
          <ShieldCheck className="w-4 h-4" />
          <span>Pending Approvals ({pendingApprovals.length})</span>
        </button>

        <button
          onClick={() => setActiveTab("orders")}
          className={`flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-semibold transition ${
            activeTab === "orders"
              ? "bg-blue-600 text-white shadow-md shadow-blue-500/20"
              : "bg-slate-900 text-slate-400 hover:text-slate-200"
          }`}
        >
          <History className="w-4 h-4" />
          <span>Issued Purchase Orders ({purchaseOrders.length})</span>
        </button>
      </div>

      {/* Tab 1: Pending Approvals */}
      {activeTab === "pending" && (
        <>
          {loading ? (
            <LoadingSpinner message="Loading pending proposal queue..." />
          ) : !isManagerOrAdmin ? (
            <EmptyState
              title="Manager Authorization Required"
              description="Switch your active user role to Manager or Admin in the top-right navbar to view pending approval queues."
              icon={Lock}
            />
          ) : pendingApprovals.length === 0 ? (
            <EmptyState
              title="No Pending Proposals"
              description="All purchase proposals have been reviewed and processed. New draft requests generated by operators or AI copilot will appear here."
              icon={CheckCircle2}
            />
          ) : (
            <div className="space-y-4">
              {pendingApprovals.map((proposal) => (
                <div
                  key={proposal.request_id}
                  className="p-6 rounded-2xl bg-slate-900/90 border border-slate-800 shadow-md space-y-4"
                >
                  {/* Proposal Header */}
                  <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 pb-4 border-b border-slate-800">
                    <div>
                      <div className="flex items-center space-x-2.5">
                        <span className="font-mono text-sm font-bold text-blue-400">
                          {proposal.request_number}
                        </span>
                        <StatusBadge status={proposal.status} />
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">
                          {proposal.priority} PRIORITY
                        </span>
                      </div>
                      <p className="text-xs text-slate-300 font-semibold mt-1">
                        Supplier:{" "}
                        <span className="text-slate-100">{proposal.supplier_name}</span>{" "}
                        (ID: {proposal.supplier_id})
                      </p>
                      <p className="text-[11px] text-slate-500">
                        Requested by: {proposal.requester_name || "AI Agent"} •{" "}
                        {new Date(proposal.created_at).toLocaleString()}
                      </p>
                    </div>

                    {/* Total & Action Buttons */}
                    <div className="flex items-center space-x-3">
                      <div className="text-right mr-2">
                        <p className="text-[10px] text-slate-400 uppercase font-medium">
                          Total Estimate
                        </p>
                        <p className="text-lg font-bold text-slate-100">
                          {formatCurrency(proposal.total_estimated_cost)}
                        </p>
                      </div>

                      <button
                        onClick={() => handleOpenReject(proposal)}
                        className="px-3 py-2 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30 text-xs font-semibold transition"
                      >
                        Reject
                      </button>

                      <button
                        onClick={() => handleOpenApprove(proposal)}
                        className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-md shadow-emerald-600/20 transition flex items-center space-x-1.5"
                      >
                        <CheckCircle2 className="w-4 h-4" />
                        <span>Approve & Issue PO</span>
                      </button>
                    </div>
                  </div>

                  {/* Proposal Reason */}
                  {proposal.reason && (
                    <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 text-xs text-slate-300">
                      <span className="font-semibold text-slate-400">Business Rationale: </span>
                      {proposal.reason}
                    </div>
                  )}

                  {/* Line Items Table */}
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead>
                        <tr className="border-b border-slate-800 text-slate-400 font-semibold uppercase">
                          <th className="py-2 px-3">Product Name & SKU</th>
                          <th className="py-2 px-3">Quantity</th>
                          <th className="py-2 px-3">Contract Unit Cost</th>
                          <th className="py-2 px-3 text-right">Line Total</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 font-mono">
                        {proposal.items.map((item) => (
                          <tr key={item.id} className="hover:bg-slate-800/30">
                            <td className="py-2.5 px-3">
                              <span className="font-sans font-medium text-slate-200">
                                {item.product_name}
                              </span>
                              <span className="text-[11px] text-slate-500 ml-2">
                                ({item.product_sku})
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-slate-300">
                              {item.quantity}
                            </td>
                            <td className="py-2.5 px-3 text-slate-300">
                              {formatCurrency(item.estimated_unit_cost)}
                            </td>
                            <td className="py-2.5 px-3 text-right font-semibold text-slate-100">
                              {formatCurrency(item.total_cost)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Version Hash Badge */}
                  <div className="flex items-center justify-between pt-2 text-[11px] text-slate-500 border-t border-slate-800/60 font-mono">
                    <div className="flex items-center space-x-1">
                      <Hash className="w-3.5 h-3.5 text-slate-400" />
                      <span>SHA-256 Proposal Integrity Hash:</span>
                      <span className="text-slate-400 truncate max-w-xs">
                        {proposal.proposal_version_hash}
                      </span>
                    </div>
                    <span>{proposal.items_count} verified line items</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* Tab 2: Issued Purchase Orders */}
      {activeTab === "orders" && (
        <>
          {loading ? (
            <LoadingSpinner message="Loading purchase order ledger..." />
          ) : purchaseOrders.length === 0 ? (
            <EmptyState
              title="No Purchase Orders Issued Yet"
              description="When pending proposals are approved, converted purchase orders will appear here."
              icon={FileCheck}
            />
          ) : (
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl overflow-hidden shadow-sm">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-slate-800 bg-slate-950/60 text-slate-400 font-semibold uppercase">
                      <th className="py-3 px-4">PO Number</th>
                      <th className="py-3 px-4">Supplier</th>
                      <th className="py-3 px-4">Items Breakdown</th>
                      <th className="py-3 px-4">Total Amount</th>
                      <th className="py-3 px-4">Status</th>
                      <th className="py-3 px-4">Approved Date</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {purchaseOrders.map((po) => (
                      <tr key={po.id} className="hover:bg-slate-800/40 transition">
                        <td className="py-3.5 px-4 font-mono font-bold text-blue-400">
                          {po.order_number}
                        </td>
                        <td className="py-3.5 px-4 font-medium text-slate-200">
                          {po.supplier_name || `Supplier ID ${po.supplier_id}`}
                        </td>
                        <td className="py-3.5 px-4 text-slate-300">
                          {po.items.map((it) => (
                            <div key={it.id} className="text-[11px]">
                              {it.quantity}x {it.product_name || `SKU ${it.product_id}`}
                            </div>
                          ))}
                        </td>
                        <td className="py-3.5 px-4 font-semibold text-slate-100">
                          {formatCurrency(po.total_amount)}
                        </td>
                        <td className="py-3.5 px-4">
                          <StatusBadge status={po.status} type="order" />
                        </td>
                        <td className="py-3.5 px-4 text-slate-400">
                          {po.approved_at
                            ? new Date(po.approved_at).toLocaleString()
                            : new Date(po.created_at).toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}

      {/* Approve Confirmation Modal */}
      <Modal
        isOpen={approveModalOpen}
        onClose={() => setApproveModalOpen(false)}
        title={`Authorize & Issue PO — ${selectedProposal?.request_number}`}
      >
        <form onSubmit={handleExecuteApprove} className="space-y-4 text-xs">
          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
            <div className="flex justify-between">
              <span className="text-slate-400">Supplier:</span>
              <span className="font-semibold text-slate-200">
                {selectedProposal?.supplier_name}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Total Commitment:</span>
              <span className="font-bold text-emerald-400 text-sm">
                {formatCurrency(selectedProposal?.total_estimated_cost || 0)}
              </span>
            </div>
            <div className="flex justify-between font-mono text-[11px] text-slate-500 pt-2 border-t border-slate-800">
              <span>Proposal SHA-256:</span>
              <span className="truncate max-w-[200px]">
                {selectedProposal?.proposal_version_hash}
              </span>
            </div>
          </div>

          <div>
            <label className="block text-slate-300 font-semibold mb-1">
              Approver Notes (Optional)
            </label>
            <textarea
              rows={3}
              value={approvalNotes}
              onChange={(e) => setApprovalNotes(e.target.value)}
              className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 text-xs focus:outline-none focus:border-blue-500"
              placeholder="Add internal manager authorization remarks..."
            />
          </div>

          <div className="flex items-center justify-end space-x-3 pt-3 border-t border-slate-800">
            <button
              type="button"
              onClick={() => setApproveModalOpen(false)}
              className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 hover:bg-slate-700 font-semibold"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={actionLoading}
              className="px-5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold disabled:opacity-50 transition shadow-md shadow-emerald-600/20"
            >
              {actionLoading ? "Dispatching..." : "Confirm & Dispatch PO"}
            </button>
          </div>
        </form>
      </Modal>

      {/* Reject Confirmation Modal */}
      <Modal
        isOpen={rejectModalOpen}
        onClose={() => setRejectModalOpen(false)}
        title={`Reject Proposal — ${selectedProposal?.request_number}`}
      >
        <form onSubmit={handleExecuteReject} className="space-y-4 text-xs">
          <p className="text-slate-300">
            Please supply a mandatory justification for rejecting this purchase request:
          </p>

          <div>
            <label className="block text-slate-300 font-semibold mb-1">
              Rejection Reason *
            </label>
            <textarea
              rows={3}
              required
              minLength={3}
              value={rejectionReason}
              onChange={(e) => setRejectionReason(e.target.value)}
              className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 text-xs focus:outline-none focus:border-rose-500"
              placeholder="e.g. Budget limit exceeded for this category / Supplier contract under renegotiation"
            />
          </div>

          <div className="flex items-center justify-end space-x-3 pt-3 border-t border-slate-800">
            <button
              type="button"
              onClick={() => setRejectModalOpen(false)}
              className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 hover:bg-slate-700 font-semibold"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={actionLoading || !rejectionReason.trim()}
              className="px-5 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-semibold disabled:opacity-50 transition shadow-md shadow-rose-600/20"
            >
              {actionLoading ? "Rejecting..." : "Confirm Rejection"}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
