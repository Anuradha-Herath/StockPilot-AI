"use client";

import React, { Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  AlertCircle,
  Bot,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  FileCheck,
  Hash,
  Loader2,
  Lock,
  Package,
  Plus,
  RefreshCw,
  Send,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Terminal,
  Trash2,
  User as UserIcon,
  XCircle,
} from "lucide-react";
import { api } from "@/lib/api";
import { ChatMessage, ToolCallLog, OrderExecutionResult } from "@/lib/types";
import { useUser } from "@/context/UserContext";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Modal } from "@/components/common/Modal";

const STARTER_PROMPTS = [
  "Show all products running low on stock",
  "Which suppliers can provide whole milk and what are their rates?",
  "Calculate replenishment recommendation for Honeycrisp Apples",
  "Please create a draft purchase order to restock all critical low-stock items.",
];

interface ProposalCardData {
  id: number;
  request_number: string;
  supplier_id: number;
  supplier_name: string;
  status: string;
  priority: string;
  reason?: string;
  total_estimated_cost: number | string;
  items: Array<{
    id?: number;
    product_id: number;
    product_sku?: string;
    product_name?: string;
    quantity: number;
    estimated_unit_cost: number | string;
    total_cost: number | string;
  }>;
  proposal_version_hash?: string;
  created_at?: string;
  next_step?: string;
  po_number?: string;
  transmission_id?: string;
}

function AssistantChat() {
  const { currentUser, isManagerOrAdmin } = useUser();
  const searchParams = useSearchParams();
  const urlPrompt = searchParams.get("prompt");

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string>("");
  const [expandedTools, setExpandedTools] = useState<Record<string, boolean>>({});

  // Proposal modal & action states
  const [selectedProposal, setSelectedProposal] = useState<ProposalCardData | null>(null);
  const [approveModalOpen, setApproveModalOpen] = useState(false);
  const [rejectModalOpen, setRejectModalOpen] = useState(false);
  const [approvalNotes, setApprovalNotes] = useState("");
  const [rejectionReason, setRejectionReason] = useState("");
  const [actionLoading, setActionLoading] = useState(false);
  const [cardStatusOverrides, setCardStatusOverrides] = useState<
    Record<
      number,
      {
        status: string;
        po_number?: string;
        transmission_id?: string;
        comments?: string;
      }
    >
  >({});

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Initialize session ID and restore persistent chat messages
  useEffect(() => {
    let sid = localStorage.getItem("stockpilot_chat_session");
    if (!sid) {
      sid = `session_${Math.random().toString(36).substring(2, 10)}`;
      localStorage.setItem("stockpilot_chat_session", sid);
    }
    setSessionId(sid);

    const saved = localStorage.getItem(`stockpilot_chat_msgs_${sid}`);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) {
          setMessages(parsed);
          return;
        }
      } catch (e) {
        console.error("Failed to parse stored chat messages", e);
      }
    }

    // Default welcome greeting
    const defaultWelcome: ChatMessage = {
      id: "msg_welcome",
      role: "assistant",
      content: `👋 Hello ${currentUser.full_name.split(" ")[0]}! I am **StockPilot AI**, your intelligent inventory and procurement copilot.\n\nI can analyze catalog levels, inspect supplier lead times and pricing, calculate optimal replenishment quantities, and prepare draft purchase requests for review. What would you like to check today?`,
      timestamp: new Date().toISOString(),
    };
    setMessages([defaultWelcome]);
    localStorage.setItem(`stockpilot_chat_msgs_${sid}`, JSON.stringify([defaultWelcome]));
  }, [currentUser]);

  // Persist messages whenever they change
  useEffect(() => {
    if (sessionId && messages.length > 0) {
      localStorage.setItem(`stockpilot_chat_msgs_${sessionId}`, JSON.stringify(messages));
    }
  }, [messages, sessionId]);

  // Handle URL prompt if provided
  useEffect(() => {
    if (urlPrompt && messages.length > 0 && !loading) {
      setInputMessage(urlPrompt);
    }
  }, [urlPrompt]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSendMessage = async (textToSend?: string) => {
    const text = textToSend || inputMessage;
    if (!text.trim() || loading) return;

    const userMsg: ChatMessage = {
      id: `user_${Date.now()}`,
      role: "user",
      content: text,
      timestamp: new Date().toISOString(),
    };

    const newMessages = [...messages, userMsg];
    setMessages(newMessages);
    setInputMessage("");
    setLoading(true);

    try {
      // Build conversation history format for backend
      const history = newMessages
        .filter((m) => m.id !== "msg_welcome")
        .map((m) => ({
          role: m.role,
          content: m.content,
        }));

      const response = await api.sendChat({
        message: text,
        session_id: sessionId,
        history,
      });

      const assistantMsg: ChatMessage = {
        id: `ai_${Date.now()}`,
        role: "assistant",
        content: response.reply,
        timestamp: new Date().toISOString(),
        tool_calls: response.tool_calls,
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: `err_${Date.now()}`,
        role: "assistant",
        content: `⚠️ **Error communicating with AI engine:** ${
          err.response?.data?.error?.message || err.message || "Unknown error"
        }\n\nPlease ensure the backend service is active.`,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleClearChat = () => {
    if (sessionId) {
      localStorage.removeItem(`stockpilot_chat_msgs_${sessionId}`);
    }
    const newSid = `session_${Math.random().toString(36).substring(2, 10)}`;
    localStorage.setItem("stockpilot_chat_session", newSid);
    setSessionId(newSid);
    const welcomeMsg: ChatMessage = {
      id: `msg_welcome_${Date.now()}`,
      role: "assistant",
      content: `Conversation reset. Session ID: \`${newSid}\`.\n\nHow can I help you manage inventory and procurement today?`,
      timestamp: new Date().toISOString(),
    };
    setMessages([welcomeMsg]);
    localStorage.setItem(`stockpilot_chat_msgs_${newSid}`, JSON.stringify([welcomeMsg]));
  };

  const toggleToolExpand = (toolKey: string) => {
    setExpandedTools((prev) => ({
      ...prev,
      [toolKey]: !prev[toolKey],
    }));
  };

  const formatCurrency = (val: number | string) => {
    const num = typeof val === "string" ? parseFloat(val) : val;
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(num || 0);
  };

  // Extract proposal from a tool call if it created a draft purchase request
  const extractProposalFromTool = (tool: ToolCallLog): ProposalCardData | null => {
    if (tool.tool_name === "create_draft_purchase_request" && tool.data && tool.data.request_number) {
      const d = tool.data;
      return {
        id: d.id || d.request_id,
        request_number: d.request_number,
        supplier_id: d.supplier_id,
        supplier_name: d.supplier_name,
        status: d.status,
        priority: d.priority,
        reason: d.reason,
        total_estimated_cost: d.total_estimated_cost,
        items: d.items || [],
        proposal_version_hash: d.proposal_version_hash,
        created_at: d.created_at,
        next_step: d.next_step,
      };
    }
    return null;
  };

  const handleOpenApproveProposal = (proposal: ProposalCardData) => {
    setSelectedProposal(proposal);
    setApprovalNotes(`Approved by ${currentUser.full_name} directly via StockPilot Copilot chat.`);
    setApproveModalOpen(true);
  };

  const handleOpenRejectProposal = (proposal: ProposalCardData) => {
    setSelectedProposal(proposal);
    setRejectionReason("");
    setRejectModalOpen(true);
  };

  const handleExecuteApprove = async (e: React.FormEvent) => {
    e.preventDefault();
    const targetId = selectedProposal?.id || (selectedProposal as any)?.request_id;
    if (!selectedProposal || !targetId) return;

    try {
      setActionLoading(true);
      const idempotencyKey = `idemp_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;
      const result: OrderExecutionResult = await api.approveRequest(targetId, {
        proposal_version_hash: selectedProposal.proposal_version_hash || "",
        comments: approvalNotes,
        idempotency_key: idempotencyKey,
      });

      setCardStatusOverrides((prev) => ({
        ...prev,
        [targetId]: {
          status: "APPROVED",
          po_number: result.order_number,
          transmission_id: result.transmission_id,
          comments: approvalNotes,
        },
      }));

      setApproveModalOpen(false);
    } catch (err: any) {
      const msg =
        err.response?.data?.error?.message ||
        err.response?.data?.message ||
        err.message ||
        "Failed to approve proposal";
      alert(`Approval Failed: ${msg}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleExecuteReject = async (e: React.FormEvent) => {
    e.preventDefault();
    const targetId = selectedProposal?.id || (selectedProposal as any)?.request_id;
    if (!selectedProposal || !targetId || !rejectionReason.trim()) return;

    try {
      setActionLoading(true);
      await api.rejectRequest(targetId, {
        comments: rejectionReason,
      });

      setCardStatusOverrides((prev) => ({
        ...prev,
        [targetId]: {
          status: "REJECTED",
          comments: rejectionReason,
        },
      }));

      setRejectModalOpen(false);
    } catch (err: any) {
      const msg =
        err.response?.data?.error?.message ||
        err.response?.data?.message ||
        err.message ||
        "Failed to reject proposal";
      alert(`Rejection Failed: ${msg}`);
    } finally {
      setActionLoading(false);
    }
  };

  // Helper to format text with rich markdown
  const renderFormattedText = (text?: string | null) => {
    if (!text) return null;
    const lines = String(text).split("\n");
    const blocks: React.ReactNode[] = [];
    let i = 0;

    while (i < lines.length) {
      const line = lines[i];

      // Table Detection
      if (line.trim().startsWith("|") && line.trim().endsWith("|")) {
        const tableLines: string[] = [];
        while (
          i < lines.length &&
          lines[i].trim().startsWith("|") &&
          lines[i].trim().endsWith("|")
        ) {
          tableLines.push(lines[i].trim());
          i++;
        }

        if (tableLines.length >= 2) {
          const headerCells = tableLines[0]
            .split("|")
            .map((c) => c.trim())
            .filter((c, idx, arr) => idx !== 0 && idx !== arr.length - 1);

          const dataRows = tableLines.slice(1).filter((r) => !r.includes("---"));

          blocks.push(
            <div
              key={`table_${i}`}
              className="my-3 overflow-x-auto rounded-xl border border-slate-800 bg-slate-950/80 shadow-md"
            >
              <table className="w-full text-left text-xs divide-y divide-slate-800">
                <thead className="bg-slate-900/90 text-slate-300 font-semibold uppercase tracking-wider">
                  <tr>
                    {headerCells.map((h, hIdx) => (
                      <th key={hIdx} className="py-2.5 px-3 whitespace-nowrap">
                        {parseInline(h)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {dataRows.map((row, rIdx) => {
                    const cells = row
                      .split("|")
                      .map((c) => c.trim())
                      .filter((c, idx, arr) => idx !== 0 && idx !== arr.length - 1);
                    return (
                      <tr key={rIdx} className="hover:bg-slate-900/40 transition">
                        {cells.map((cell, cIdx) => (
                          <td key={cIdx} className="py-2.5 px-3 text-slate-200">
                            {parseInline(cell)}
                          </td>
                        ))}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          );
          continue;
        }
      }

      // Headings
      if (line.startsWith("### ")) {
        blocks.push(
          <h4
            key={i}
            className="text-sm font-bold text-slate-100 mt-3 mb-1.5 flex items-center space-x-2"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-blue-500 inline-block" />
            <span>{line.replace("### ", "")}</span>
          </h4>
        );
        i++;
        continue;
      }
      if (line.startsWith("## ")) {
        blocks.push(
          <h3
            key={i}
            className="text-base font-bold text-slate-100 mt-3.5 mb-2 border-b border-slate-800/80 pb-1"
          >
            {line.replace("## ", "")}
          </h3>
        );
        i++;
        continue;
      }

      // Bullet list items
      if (line.startsWith("- ") || line.startsWith("* ")) {
        blocks.push(
          <li key={i} className="ml-4 list-disc text-slate-300 my-0.5 leading-relaxed">
            {parseInline(line.substring(2))}
          </li>
        );
        i++;
        continue;
      }

      // Numbered list items
      const numMatch = line.match(/^(\d+)\.\s+(.*)$/);
      if (numMatch) {
        blocks.push(
          <div key={i} className="flex items-start space-x-2 my-1.5 ml-1 text-slate-300">
            <span className="px-1.5 py-0.2 rounded bg-slate-800 text-blue-400 font-mono text-[11px] font-bold shrink-0">
              {numMatch[1]}
            </span>
            <div className="flex-1 leading-relaxed">{parseInline(numMatch[2])}</div>
          </div>
        );
        i++;
        continue;
      }

      // Blockquotes
      if (line.startsWith("> ")) {
        blocks.push(
          <blockquote
            key={i}
            className="border-l-2 border-blue-500/60 pl-3 py-1.5 my-2 bg-blue-500/10 text-blue-300 text-xs rounded-r-lg font-medium"
          >
            {parseInline(line.replace("> ", ""))}
          </blockquote>
        );
        i++;
        continue;
      }

      // Horizontal Rules
      if (line.trim() === "---" || line.trim() === "***") {
        blocks.push(<hr key={i} className="my-3 border-slate-800" />);
        i++;
        continue;
      }

      // Empty lines
      if (line.trim() === "") {
        blocks.push(<div key={i} className="h-1.5" />);
        i++;
        continue;
      }

      // Normal paragraphs
      blocks.push(
        <p key={i} className="my-1 text-slate-200 leading-relaxed">
          {parseInline(line)}
        </p>
      );
      i++;
    }

    return blocks;
  };

  const parseInline = (text: string) => {
    const parts = text.split(/(\*\*.*?\*\*|`.*?`)/g);
    return parts.map((part, i) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return (
          <strong key={i} className="text-slate-100 font-bold">
            {part.slice(2, -2)}
          </strong>
        );
      }
      if (part.startsWith("`") && part.endsWith("`")) {
        return (
          <code
            key={i}
            className="px-1.5 py-0.5 rounded bg-slate-800 text-blue-300 font-mono text-xs border border-slate-700"
          >
            {part.slice(1, -1)}
          </code>
        );
      }
      return part;
    });
  };

  return (
    <div className="flex flex-col h-[calc(100vh-8.5rem)] rounded-2xl bg-slate-900/90 border border-slate-800 overflow-hidden shadow-2xl">
      {/* Chat Top Bar */}
      <div className="flex items-center justify-between px-6 py-3.5 border-b border-slate-800 bg-slate-950/60">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 shadow-md shadow-blue-500/20">
            <Bot className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="text-sm font-bold text-slate-100">StockPilot Copilot</h2>
              <span className="px-1.5 py-0.2 rounded text-[10px] font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                LangGraph State Machine
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-mono">
              Session: {sessionId}
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <Link
            href="/approvals"
            className="hidden sm:flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-purple-900/30 hover:bg-purple-900/50 text-purple-300 text-xs font-semibold border border-purple-700/50 transition"
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Approval Center</span>
          </Link>

          <button
            onClick={handleClearChat}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-slate-100 text-xs font-medium border border-slate-700 transition"
            title="Reset conversation and start fresh session"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>New Session</span>
          </button>
        </div>
      </div>

      {/* Messages Stream Container */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.map((msg) => {
          const isUser = msg.role === "user";

          // Find any purchase proposal generated in this turn
          const proposals: ProposalCardData[] = [];
          if (msg.tool_calls) {
            for (const tool of msg.tool_calls) {
              const prop = extractProposalFromTool(tool);
              if (prop) proposals.push(prop);
            }
          }

          return (
            <div
              key={msg.id}
              className={`flex items-start space-x-3 ${
                isUser ? "flex-row-reverse space-x-reverse" : ""
              }`}
            >
              {/* Avatar */}
              <div
                className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 text-xs font-bold ${
                  isUser
                    ? "bg-blue-600 text-white shadow-md shadow-blue-600/30"
                    : "bg-slate-800 border border-slate-700 text-blue-400"
                }`}
              >
                {isUser ? <UserIcon className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
              </div>

              {/* Message Bubble & Cards */}
              <div className={`max-w-2xl space-y-3 w-full ${isUser ? "items-end" : "items-start"}`}>
                <div
                  className={`p-4 rounded-2xl text-xs leading-relaxed ${
                    isUser
                      ? "bg-blue-600 text-white rounded-tr-none shadow-md shadow-blue-500/10 font-medium"
                      : "bg-slate-950/80 border border-slate-800 rounded-tl-none text-slate-200"
                  }`}
                >
                  {isUser ? msg.content : renderFormattedText(msg.content)}
                </div>

                {/* Purchase Proposal Cards */}
                {proposals.map((proposal) => {
                  const override = cardStatusOverrides[proposal.id];
                  const currentStatus = override?.status || proposal.status || "PENDING_APPROVAL";
                  const poNumber = override?.po_number || proposal.po_number;
                  const isApproved = currentStatus === "APPROVED" || currentStatus === "CONVERTED_TO_PO";
                  const isRejected = currentStatus === "REJECTED";
                  const isPending = !isApproved && !isRejected;

                  return (
                    <div
                      key={`prop_card_${proposal.id}`}
                      className="p-5 rounded-2xl bg-gradient-to-b from-slate-900 via-slate-900/95 to-slate-950 border-2 border-indigo-500/30 shadow-xl space-y-3.5"
                    >
                      {/* Card Top Title & Status */}
                      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 pb-3 border-b border-slate-800">
                        <div>
                          <div className="flex items-center space-x-2">
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                              PROPOSAL CARD
                            </span>
                            <span className="font-mono text-sm font-bold text-blue-400">
                              {proposal.request_number}
                            </span>
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                isApproved
                                  ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                                  : isRejected
                                  ? "bg-rose-500/20 text-rose-400 border border-rose-500/30"
                                  : "bg-purple-500/20 text-purple-300 border border-purple-500/30"
                              }`}
                            >
                              {currentStatus}
                            </span>
                          </div>
                          <p className="text-xs text-slate-300 font-semibold mt-1">
                            Supplier:{" "}
                            <span className="text-slate-100">{proposal.supplier_name}</span>{" "}
                            <span className="text-slate-500 font-mono">(ID: {proposal.supplier_id})</span>
                          </p>
                        </div>

                        <div className="text-right">
                          <p className="text-[10px] text-slate-400 uppercase font-medium">
                            Estimated Total
                          </p>
                          <p className="text-base font-bold text-emerald-400">
                            {formatCurrency(proposal.total_estimated_cost)}
                          </p>
                        </div>
                      </div>

                      {/* Business Reason */}
                      {proposal.reason && (
                        <div className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80 text-[11px] text-slate-300">
                          <span className="font-semibold text-slate-400">Reason: </span>
                          {proposal.reason}
                        </div>
                      )}

                      {/* Items Table */}
                      <div className="overflow-x-auto rounded-xl border border-slate-800/80 bg-slate-950/40">
                        <table className="w-full text-left text-[11px]">
                          <thead className="bg-slate-900/60 text-slate-400 font-semibold uppercase border-b border-slate-800/80">
                            <tr>
                              <th className="py-2 px-3">Product SKU & Name</th>
                              <th className="py-2 px-3">Quantity</th>
                              <th className="py-2 px-3">Unit Cost</th>
                              <th className="py-2 px-3 text-right">Total</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-800/40 font-mono">
                            {proposal.items.map((item, itIdx) => (
                              <tr key={itIdx} className="hover:bg-slate-800/30">
                                <td className="py-2 px-3">
                                  <span className="font-sans font-medium text-slate-200">
                                    {item.product_name || `SKU ${item.product_id}`}
                                  </span>
                                  {item.product_sku && (
                                    <span className="text-[10px] text-slate-500 ml-1.5">
                                      ({item.product_sku})
                                    </span>
                                  )}
                                </td>
                                <td className="py-2 px-3 text-slate-300 font-bold">
                                  {item.quantity}
                                </td>
                                <td className="py-2 px-3 text-slate-300">
                                  {formatCurrency(item.estimated_unit_cost)}
                                </td>
                                <td className="py-2 px-3 text-right font-bold text-slate-100">
                                  {formatCurrency(item.total_cost)}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>

                      {/* Integrity Hash */}
                      {proposal.proposal_version_hash && (
                        <div className="flex items-center space-x-1.5 text-[10px] text-slate-500 font-mono">
                          <Hash className="w-3 h-3 text-slate-400" />
                          <span>SHA-256 Hash:</span>
                          <span className="text-slate-400 truncate max-w-xs">
                            {proposal.proposal_version_hash}
                          </span>
                        </div>
                      )}

                      {/* Action Decision Area */}
                      <div className="pt-2 border-t border-slate-800/80 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                        {isPending ? (
                          <>
                            <div className="flex items-center space-x-2 text-[11px] text-slate-400">
                              <ShieldCheck className="w-4 h-4 text-purple-400" />
                              <span>Human-in-the-Loop Approval Required</span>
                            </div>

                            <div className="flex items-center space-x-2">
                              <button
                                onClick={() => handleOpenRejectProposal(proposal)}
                                className="px-3.5 py-1.5 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/30 text-xs font-semibold transition"
                              >
                                Reject Order
                              </button>

                              <button
                                onClick={() => handleOpenApproveProposal(proposal)}
                                className="px-4 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-md shadow-emerald-600/20 transition flex items-center space-x-1.5"
                              >
                                <CheckCircle2 className="w-4 h-4" />
                                <span>Approve Order</span>
                              </button>
                            </div>
                          </>
                        ) : isApproved ? (
                          <div className="w-full p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs flex items-center justify-between">
                            <div className="flex items-center space-x-2">
                              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                              <span className="font-semibold">
                                Order Approved & Issued! PO Number:{" "}
                                <strong className="font-mono text-white">{poNumber || "PO-ISSUED"}</strong>
                              </span>
                            </div>
                            <Link
                              href="/approvals"
                              className="text-[11px] underline text-emerald-400 hover:text-emerald-300 flex items-center space-x-1"
                            >
                              <span>View in Approval Center</span>
                              <ExternalLink className="w-3 h-3" />
                            </Link>
                          </div>
                        ) : (
                          <div className="w-full p-2.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center space-x-2">
                            <XCircle className="w-4 h-4 text-rose-400" />
                            <span className="font-semibold">
                              Proposal Rejected ({override?.comments || "Rejected by Manager"})
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}

                {/* Tool Execution Logs Visualizer */}
                {msg.tool_calls && msg.tool_calls.length > 0 && (
                  <div className="space-y-2 pt-1">
                    <p className="text-[11px] font-semibold uppercase text-slate-400 flex items-center space-x-1.5">
                      <Terminal className="w-3.5 h-3.5 text-blue-400" />
                      <span>Executed Database Tools ({msg.tool_calls.length})</span>
                    </p>
                    <div className="space-y-1.5">
                      {msg.tool_calls.map((tool, idx) => {
                        const toolKey = `${msg.id}_tool_${idx}`;
                        const isExpanded = !!expandedTools[toolKey];
                        return (
                          <div
                            key={idx}
                            className="rounded-xl border border-slate-800 bg-slate-950/60 overflow-hidden text-xs"
                          >
                            <button
                              onClick={() => toggleToolExpand(toolKey)}
                              className="w-full flex items-center justify-between px-3 py-2 bg-slate-900/60 hover:bg-slate-900 transition text-left"
                            >
                              <div className="flex items-center space-x-2">
                                {tool.success ? (
                                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                                ) : (
                                  <AlertCircle className="w-3.5 h-3.5 text-rose-400 shrink-0" />
                                )}
                                <span className="font-mono font-semibold text-blue-300">
                                  {tool.tool_name}
                                </span>
                              </div>
                              <div className="flex items-center space-x-2 text-[11px] text-slate-400">
                                <span>{tool.result_summary}</span>
                                {isExpanded ? (
                                  <ChevronDown className="w-3.5 h-3.5" />
                                ) : (
                                  <ChevronRight className="w-3.5 h-3.5" />
                                )}
                              </div>
                            </button>

                            {isExpanded && (
                              <div className="p-3 bg-slate-950 border-t border-slate-800/80 font-mono text-[11px] text-slate-400 overflow-x-auto space-y-1.5">
                                <p className="text-slate-500 font-bold">Arguments:</p>
                                <pre className="text-slate-300">
                                  {JSON.stringify(tool.arguments, null, 2)}
                                </pre>
                                {tool.data && (
                                  <>
                                    <p className="text-slate-500 font-bold mt-2">Result Payload:</p>
                                    <pre className="text-emerald-300">
                                      {JSON.stringify(tool.data, null, 2)}
                                    </pre>
                                  </>
                                )}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            </div>
          );
        })}

        {loading && (
          <div className="flex items-start space-x-3">
            <div className="w-8 h-8 rounded-xl bg-slate-800 border border-slate-700 text-blue-400 flex items-center justify-center shrink-0">
              <Bot className="w-4 h-4 animate-pulse" />
            </div>
            <div className="p-3.5 rounded-2xl bg-slate-950/80 border border-slate-800 rounded-tl-none flex items-center space-x-2 text-slate-400 text-xs">
              <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
              <span>Analyzing catalog & executing tools...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Quick Starter Prompts */}
      {messages.length <= 2 && (
        <div className="px-6 py-2 border-t border-slate-800/60 bg-slate-950/30 flex items-center space-x-2 overflow-x-auto">
          <span className="text-[11px] font-semibold text-slate-400 flex items-center space-x-1 shrink-0">
            <Sparkles className="w-3.5 h-3.5 text-amber-400" />
            <span>Suggested:</span>
          </span>
          {STARTER_PROMPTS.map((prompt, i) => (
            <button
              key={i}
              onClick={() => handleSendMessage(prompt)}
              className="px-3 py-1 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium border border-slate-700/60 whitespace-nowrap transition"
            >
              {prompt}
            </button>
          ))}
        </div>
      )}

      {/* Input Field Form */}
      <div className="p-4 border-t border-slate-800 bg-slate-950/80">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSendMessage();
          }}
          className="flex items-center space-x-2"
        >
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            disabled={loading}
            placeholder="Ask about inventory, supplier rates, reorder math, or draft proposals..."
            className="flex-1 px-4 py-3 rounded-xl bg-slate-900 border border-slate-800 text-slate-100 placeholder-slate-500 text-xs focus:outline-none focus:border-blue-500 transition disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={loading || !inputMessage.trim()}
            className="px-5 py-3 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs flex items-center space-x-1.5 transition disabled:opacity-50 shadow-md shadow-blue-500/20"
          >
            <span>Send</span>
            <Send className="w-3.5 h-3.5" />
          </button>
        </form>
      </div>

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

          {!isManagerOrAdmin && (
            <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-[11px] flex items-start space-x-2">
              <Lock className="w-4 h-4 shrink-0 mt-0.5" />
              <span>
                Note: Your current role is <strong>{currentUser.role}</strong>. Approvals require <strong>MANAGER</strong> or <strong>ADMIN</strong>. You can switch personas using the dropdown in the top-right navbar.
              </span>
            </div>
          )}

          <div>
            <label className="block text-slate-300 font-semibold mb-1">
              Approver Notes (Optional)
            </label>
            <textarea
              rows={3}
              value={approvalNotes}
              onChange={(e) => setApprovalNotes(e.target.value)}
              className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 text-xs focus:outline-none focus:border-blue-500"
              placeholder="Add manager authorization remarks..."
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
              placeholder="e.g. Budget limit exceeded / Supplier contract under renegotiation"
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

export default function AssistantPage() {
  return (
    <Suspense fallback={<LoadingSpinner message="Initializing AI Copilot..." size="lg" />}>
      <AssistantChat />
    </Suspense>
  );
}
