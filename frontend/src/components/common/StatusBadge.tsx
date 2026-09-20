import React from "react";
import { StockStatus, PurchaseRequestStatus, PurchaseOrderStatus } from "@/lib/types";

interface StatusBadgeProps {
  status: StockStatus | PurchaseRequestStatus | PurchaseOrderStatus | string;
  type?: "stock" | "request" | "order";
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, type = "stock" }) => {
  const getBadgeStyle = () => {
    switch (status) {
      // Stock Statuses
      case "HEALTHY":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";
      case "LOW_STOCK":
        return "bg-amber-500/10 text-amber-400 border-amber-500/30 animate-pulse";
      case "OUT_OF_STOCK":
        return "bg-rose-500/10 text-rose-400 border-rose-500/30";

      // Purchase Request & PO Statuses
      case "DRAFT":
        return "bg-slate-500/10 text-slate-300 border-slate-500/30";
      case "PENDING_APPROVAL":
        return "bg-amber-500/10 text-amber-400 border-amber-500/30";
      case "APPROVED":
        return "bg-blue-500/10 text-blue-400 border-blue-500/30";
      case "ISSUED":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";
      case "REJECTED":
        return "bg-rose-500/10 text-rose-400 border-rose-500/30";
      case "CONVERTED_TO_PO":
        return "bg-indigo-500/10 text-indigo-400 border-indigo-500/30";
      case "EXPIRED":
        return "bg-slate-600/20 text-slate-400 border-slate-600/30";
      case "CANCELLED":
        return "bg-gray-500/10 text-gray-400 border-gray-500/30";
      case "FULFILLED":
        return "bg-emerald-600/20 text-emerald-300 border-emerald-600/40";
      default:
        return "bg-slate-500/10 text-slate-400 border-slate-500/30";
    }
  };

  const formatText = (text: string) => {
    return text.replace(/_/g, " ");
  };

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getBadgeStyle()}`}
    >
      {formatText(status)}
    </span>
  );
};
