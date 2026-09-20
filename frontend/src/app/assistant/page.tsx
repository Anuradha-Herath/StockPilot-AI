"use client";

import React, { Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  AlertCircle,
  Bot,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  CornerDownLeft,
  FileText,
  Loader2,
  Package,
  Plus,
  RefreshCw,
  Send,
  ShieldAlert,
  Sparkles,
  Terminal,
  Trash2,
  User as UserIcon,
} from "lucide-react";
import { api } from "@/lib/api";
import { ChatMessage, ToolCallLog } from "@/lib/types";
import { useUser } from "@/context/UserContext";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";

const STARTER_PROMPTS = [
  "Show all products running low on stock",
  "Which suppliers can provide whole milk and what are their rates?",
  "Calculate replenishment recommendation for Honeycrisp Apples",
  "Prepare a draft purchase request for depleted bakery items",
];

function AssistantChat() {
  const { currentUser } = useUser();
  const searchParams = useSearchParams();
  const urlPrompt = searchParams.get("prompt");

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string>("");
  const [expandedTools, setExpandedTools] = useState<Record<string, boolean>>({});

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Initialize session ID
  useEffect(() => {
    let sid = localStorage.getItem("stockpilot_chat_session");
    if (!sid) {
      sid = `session_${Math.random().toString(36).substring(2, 10)}`;
      localStorage.setItem("stockpilot_chat_session", sid);
    }
    setSessionId(sid);

    // Initial greeting
    setMessages([
      {
        id: "msg_welcome",
        role: "assistant",
        content: `👋 Hello ${currentUser.full_name.split(" ")[0]}! I am **StockPilot AI**, your intelligent inventory and procurement copilot.\n\nI can analyze catalog levels, inspect supplier lead times and pricing, calculate optimal replenishment quantities, and prepare draft purchase requests for review. What would you like to check today?`,
        timestamp: new Date().toISOString(),
      },
    ]);
  }, [currentUser]);

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

    setMessages((prev) => [...prev, userMsg]);
    setInputMessage("");
    setLoading(true);

    try {
      // Build conversation history format for backend
      const history = messages
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
        }\n\nPlease ensure the backend service and Groq API key are active.`,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleClearChat = () => {
    const newSid = `session_${Math.random().toString(36).substring(2, 10)}`;
    localStorage.setItem("stockpilot_chat_session", newSid);
    setSessionId(newSid);
    setMessages([
      {
        id: `msg_welcome_${Date.now()}`,
        role: "assistant",
        content: `Conversation reset. Session ID: \`${newSid}\`.\n\nHow can I help you manage inventory and procurement today?`,
        timestamp: new Date().toISOString(),
      },
    ]);
  };

  const toggleToolExpand = (toolKey: string) => {
    setExpandedTools((prev) => ({
      ...prev,
      [toolKey]: !prev[toolKey],
    }));
  };

  // Helper to format text with rich markdown: tables, bold, bullets, numbers, blockquotes, code
  const renderFormattedText = (text?: string | null) => {
    if (!text) return null;
    const lines = String(text).split("\n");
    const blocks: React.ReactNode[] = [];
    let i = 0;

    while (i < lines.length) {
      const line = lines[i];

      // 1. Table Detection (Consecutive lines starting & ending with |)
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

          // Data rows (ignoring separator rows with ---)
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

      // 2. Headings
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

      // 3. Bullet list items
      if (line.startsWith("- ") || line.startsWith("* ")) {
        blocks.push(
          <li key={i} className="ml-4 list-disc text-slate-300 my-0.5 leading-relaxed">
            {parseInline(line.substring(2))}
          </li>
        );
        i++;
        continue;
      }

      // 4. Numbered list items
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

      // 5. Blockquotes
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

      // 6. Horizontal Rules
      if (line.trim() === "---" || line.trim() === "***") {
        blocks.push(<hr key={i} className="my-3 border-slate-800" />);
        i++;
        continue;
      }

      // 7. Empty lines
      if (line.trim() === "") {
        blocks.push(<div key={i} className="h-1.5" />);
        i++;
        continue;
      }

      // 8. Normal paragraphs
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
          <div className="p-2 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600">
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

        <button
          onClick={handleClearChat}
          className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-slate-100 text-xs font-medium border border-slate-700 transition"
          title="Reset conversation and start fresh session"
        >
          <Trash2 className="w-3.5 h-3.5" />
          <span>New Session</span>
        </button>
      </div>

      {/* Messages Stream Container */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.map((msg) => {
          const isUser = msg.role === "user";
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

              {/* Message Bubble & Tool Cards */}
              <div className={`max-w-2xl space-y-3 ${isUser ? "items-end" : "items-start"}`}>
                <div
                  className={`p-4 rounded-2xl text-xs leading-relaxed ${
                    isUser
                      ? "bg-blue-600 text-white rounded-tr-none shadow-md shadow-blue-500/10 font-medium"
                      : "bg-slate-950/80 border border-slate-800 rounded-tl-none text-slate-200"
                  }`}
                >
                  {isUser ? msg.content : renderFormattedText(msg.content)}
                </div>

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
