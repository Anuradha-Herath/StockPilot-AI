import React from "react";
import { Loader2 } from "lucide-react";

export const LoadingSpinner: React.FC<{ message?: string; size?: "sm" | "md" | "lg" }> = ({
  message = "Loading data...",
  size = "md",
}) => {
  const sizeMap = {
    sm: "w-4 h-4",
    md: "w-6 h-6",
    lg: "w-10 h-10",
  };

  return (
    <div className="flex flex-col items-center justify-center p-8 text-slate-400 space-y-3">
      <Loader2 className={`${sizeMap[size]} animate-spin text-blue-500`} />
      {message && <p className="text-sm font-medium">{message}</p>}
    </div>
  );
};
