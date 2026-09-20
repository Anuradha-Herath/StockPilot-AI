"use client";

import React, { useEffect, useState } from "react";
import {
  Activity,
  Code2,
  Eye,
  Filter,
  RefreshCw,
  Search,
  Shield,
  SlidersHorizontal,
  Terminal,
  User,
} from "lucide-react";
import { api } from "@/lib/api";
import { AuditLog } from "@/lib/types";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { EmptyState } from "@/components/common/EmptyState";
import { Modal } from "@/components/common/Modal";

export default function AuditPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [actorFilter, setActorFilter] = useState<string>("ALL");
  const [searchAction, setSearchAction] = useState("");
  const [entityFilter, setEntityFilter] = useState<string>("ALL");

  // Selected Log for Payload Modal
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);
  const [payloadModalOpen, setPayloadModalOpen] = useState(false);

  const fetchAuditLogs = async () => {
    try {
      setLoading(true);
      const res = await api.getAuditLogs({
        actor_type: actorFilter === "ALL" ? undefined : actorFilter,
        action: searchAction || undefined,
        entity_type: entityFilter === "ALL" ? undefined : entityFilter,
        size: 50,
      });
      setLogs(res.items || []);
    } catch (err) {
      console.error("Failed to load audit logs", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAuditLogs();
  }, [actorFilter, entityFilter]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchAuditLogs();
  };

  const handleOpenPayload = (log: AuditLog) => {
    setSelectedLog(log);
    setPayloadModalOpen(true);
  };

  const getActorBadge = (actorType: string) => {
    switch (actorType) {
      case "AI_AGENT":
        return "bg-blue-500/20 text-blue-400 border-blue-500/30";
      case "USER":
        return "bg-purple-500/20 text-purple-400 border-purple-500/30";
      case "SYSTEM":
        return "bg-slate-500/20 text-slate-400 border-slate-500/30";
      default:
        return "bg-slate-500/20 text-slate-400 border-slate-500/30";
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-2xl font-bold text-slate-100">
              System Audit Ledger & Provenance
            </h1>
            <span className="px-2 py-0.5 rounded text-xs font-semibold bg-blue-500/20 text-blue-400 border border-blue-500/30">
              Immutable Trace
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Complete compliance trail recording AI copilot tool actions, user overrides, manager approvals, and automated tasks.
          </p>
        </div>

        <button
          onClick={fetchAuditLogs}
          className="flex items-center space-x-2 px-3 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 text-sm font-medium border border-slate-800 transition self-start sm:self-auto"
        >
          <RefreshCw className="w-4 h-4" />
          <span>Refresh Ledger</span>
        </button>
      </div>

      {/* Filter Bar */}
      <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-3 shadow-sm">
        <form
          onSubmit={handleSearch}
          className="flex flex-col md:flex-row md:items-center gap-3"
        >
          <div className="relative flex-1">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search by action name (e.g. APPROVE_AND_ISSUE, ADJUST, DRAFT)..."
              value={searchAction}
              onChange={(e) => setSearchAction(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 placeholder-slate-500 text-sm focus:outline-none focus:border-blue-500 transition"
            />
          </div>

          <div className="flex items-center space-x-2">
            <select
              value={actorFilter}
              onChange={(e) => setActorFilter(e.target.value)}
              className="py-2.5 px-3 rounded-xl bg-slate-950 border border-slate-800 text-slate-200 text-sm focus:outline-none focus:border-blue-500"
            >
              <option value="ALL">All Actor Types</option>
              <option value="AI_AGENT">AI Agent</option>
              <option value="USER">Human User</option>
              <option value="SYSTEM">System Process</option>
            </select>

            <select
              value={entityFilter}
              onChange={(e) => setEntityFilter(e.target.value)}
              className="py-2.5 px-3 rounded-xl bg-slate-950 border border-slate-800 text-slate-200 text-sm focus:outline-none focus:border-blue-500"
            >
              <option value="ALL">All Entities</option>
              <option value="PurchaseRequest">Purchase Request</option>
              <option value="PurchaseOrder">Purchase Order</option>
              <option value="InventoryLevel">Inventory Level</option>
              <option value="Product">Product</option>
            </select>

            <button
              type="submit"
              className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold"
            >
              Filter
            </button>
          </div>
        </form>
      </div>

      {/* Audit Log Table */}
      {loading ? (
        <LoadingSpinner message="Fetching compliance audit trail..." />
      ) : logs.length === 0 ? (
        <EmptyState
          title="No Audit Records Found"
          description="No action events matched the specified filter criteria."
        />
      ) : (
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-950/60 text-slate-400 font-semibold uppercase">
                  <th className="py-3 px-4">Timestamp (UTC)</th>
                  <th className="py-3 px-4">Actor</th>
                  <th className="py-3 px-4">Action</th>
                  <th className="py-3 px-4">Target Entity</th>
                  <th className="py-3 px-4">Description</th>
                  <th className="py-3 px-4 text-right">Payload</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {logs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-800/40 transition">
                    <td className="py-3.5 px-4 text-slate-400 text-[11px] whitespace-nowrap">
                      {new Date(log.timestamp).toLocaleString()}
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="flex items-center space-x-1.5">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold border ${getActorBadge(
                            log.actor_type
                          )}`}
                        >
                          {log.actor_type}
                        </span>
                        <span className="text-slate-400 text-[11px]">
                          {log.actor_id || "system"}
                        </span>
                      </div>
                    </td>
                    <td className="py-3.5 px-4 font-semibold text-slate-200">
                      {log.action}
                    </td>
                    <td className="py-3.5 px-4 text-blue-400">
                      {log.entity_type} {log.entity_id ? `#${log.entity_id}` : ""}
                    </td>
                    <td className="py-3.5 px-4 font-sans text-slate-300 max-w-sm truncate">
                      {log.description || "-"}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      {(log.payload_before || log.payload_after) && (
                        <button
                          onClick={() => handleOpenPayload(log)}
                          className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-blue-400 text-xs font-semibold border border-slate-700 transition"
                        >
                          <Code2 className="w-3.5 h-3.5" />
                          <span>View JSON</span>
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Payload JSON Modal */}
      <Modal
        isOpen={payloadModalOpen}
        onClose={() => setPayloadModalOpen(false)}
        title={`Audit Payload Detail — Event #${selectedLog?.id}`}
        maxWidth="lg"
      >
        <div className="space-y-4 text-xs font-mono">
          <div className="flex items-center justify-between p-3 rounded-xl bg-slate-950 border border-slate-800">
            <div>
              <span className="text-slate-400">Action: </span>
              <span className="font-bold text-slate-100">{selectedLog?.action}</span>
            </div>
            <div>
              <span className="text-slate-400">Actor: </span>
              <span className="text-blue-400">
                {selectedLog?.actor_type} ({selectedLog?.actor_id})
              </span>
            </div>
          </div>

          {selectedLog?.payload_before && (
            <div>
              <p className="text-slate-400 font-bold mb-1">State Before:</p>
              <pre className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-amber-300 text-[11px] overflow-x-auto">
                {JSON.stringify(selectedLog.payload_before, null, 2)}
              </pre>
            </div>
          )}

          {selectedLog?.payload_after && (
            <div>
              <p className="text-slate-400 font-bold mb-1">State After:</p>
              <pre className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-emerald-300 text-[11px] overflow-x-auto">
                {JSON.stringify(selectedLog.payload_after, null, 2)}
              </pre>
            </div>
          )}

          <div className="flex justify-end pt-2">
            <button
              onClick={() => setPayloadModalOpen(false)}
              className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 hover:bg-slate-700 text-xs font-semibold"
            >
              Close
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
