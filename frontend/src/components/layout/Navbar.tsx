"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Bot,
  CheckCircle2,
  ChevronDown,
  LayoutDashboard,
  Package,
  ShieldAlert,
  ShieldCheck,
  User as UserIcon,
  Activity,
} from "lucide-react";
import { PRESET_USERS, useUser } from "@/context/UserContext";
import { apiClient } from "@/lib/api";

export const Navbar: React.FC = () => {
  const { currentUser, switchUser } = useUser();
  const pathname = usePathname();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await apiClient.get("/health");
        setBackendOnline(res.status === 200);
      } catch {
        setBackendOnline(false);
      }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const navItems = [
    { label: "Dashboard", href: "/", icon: LayoutDashboard },
    { label: "Inventory", href: "/inventory", icon: Package },
    { label: "AI Assistant", href: "/assistant", icon: Bot },
    { label: "Approval Center", href: "/approvals", icon: ShieldCheck },
    { label: "Audit History", href: "/audit", icon: Activity },
  ];

  return (
    <header className="sticky top-0 z-40 w-full bg-slate-950/90 backdrop-blur-md border-b border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center space-x-8">
          <Link href="/" className="flex items-center space-x-3 group">
            <div className="p-2 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 shadow-lg shadow-blue-500/20 group-hover:scale-105 transition">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-lg font-bold text-slate-100 tracking-tight">
                  StockPilot
                </span>
                <span className="px-1.5 py-0.5 text-[10px] font-semibold bg-blue-500/20 text-blue-400 border border-blue-500/30 rounded">
                  AI COPILOT
                </span>
              </div>
              <p className="text-[11px] text-slate-400">Autonomous Procurement</p>
            </div>
          </Link>

          {/* Desktop Nav Links */}
          <nav className="hidden md:flex items-center space-x-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center space-x-2 px-3.5 py-2 rounded-lg text-sm font-medium transition ${
                    isActive
                      ? "bg-slate-800 text-blue-400 font-semibold shadow-inner"
                      : "text-slate-300 hover:text-slate-100 hover:bg-slate-900"
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? "text-blue-400" : "text-slate-400"}`} />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Right Section: Backend Status & Persona Switcher */}
        <div className="flex items-center space-x-4">
          {/* Backend Status Pill */}
          <div className="hidden sm:flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-xs border border-slate-800 bg-slate-900/60">
            <span
              className={`w-2 h-2 rounded-full ${
                backendOnline === true
                  ? "bg-emerald-500 animate-pulse"
                  : backendOnline === false
                  ? "bg-rose-500"
                  : "bg-amber-500"
              }`}
            />
            <span className="text-slate-400 font-medium">
              {backendOnline === true ? "API Connected" : backendOnline === false ? "API Offline" : "Connecting..."}
            </span>
          </div>

          {/* Persona Switcher Dropdown */}
          <div className="relative">
            <button
              onClick={() => setDropdownOpen(!dropdownOpen)}
              className="flex items-center space-x-2.5 px-3 py-1.5 rounded-xl border border-slate-700 bg-slate-900 hover:border-slate-600 transition"
            >
              <div
                className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold ${
                  currentUser.role === "MANAGER"
                    ? "bg-purple-600/30 text-purple-300 border border-purple-500/40"
                    : currentUser.role === "ADMIN"
                    ? "bg-blue-600/30 text-blue-300 border border-blue-500/40"
                    : "bg-emerald-600/30 text-emerald-300 border border-emerald-500/40"
                }`}
              >
                {currentUser.role[0]}
              </div>
              <div className="text-left hidden sm:block">
                <p className="text-xs font-semibold text-slate-200 truncate max-w-[140px]">
                  {currentUser.full_name}
                </p>
                <p className="text-[10px] text-slate-400 uppercase font-medium">
                  {currentUser.role}
                </p>
              </div>
              <ChevronDown className="w-4 h-4 text-slate-400" />
            </button>

            {dropdownOpen && (
              <div className="absolute right-0 mt-2 w-72 bg-slate-900 border border-slate-800 rounded-xl shadow-2xl z-50 p-2 animate-fadeIn">
                <div className="px-3 py-2 border-b border-slate-800">
                  <p className="text-xs font-semibold text-slate-300">Simulate User Role</p>
                  <p className="text-[11px] text-slate-500">
                    Switch personas to test backend RBAC & Approval gates
                  </p>
                </div>
                <div className="mt-1 space-y-1">
                  {PRESET_USERS.map((user) => {
                    const isSelected = user.id === currentUser.id;
                    return (
                      <button
                        key={user.id}
                        onClick={() => {
                          switchUser(user);
                          setDropdownOpen(false);
                        }}
                        className={`w-full text-left flex items-center justify-between p-2 rounded-lg text-xs transition ${
                          isSelected
                            ? "bg-slate-800 text-slate-100 font-semibold"
                            : "text-slate-300 hover:bg-slate-800/50 hover:text-slate-100"
                        }`}
                      >
                        <div className="flex items-center space-x-2.5">
                          <span
                            className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                              user.role === "MANAGER"
                                ? "bg-purple-500/20 text-purple-400 border border-purple-500/30"
                                : user.role === "ADMIN"
                                ? "bg-blue-500/20 text-blue-400 border border-blue-500/30"
                                : "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                            }`}
                          >
                            {user.role}
                          </span>
                          <div>
                            <p className="font-medium">{user.full_name}</p>
                            <p className="text-[10px] text-slate-500">{user.email}</p>
                          </div>
                        </div>
                        {isSelected && <CheckCircle2 className="w-4 h-4 text-blue-400" />}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};
