"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { User, UserRole } from "@/lib/types";

export const PRESET_USERS: User[] = [
  {
    id: 2,
    email: "sarah.procurement@freshmarket.com",
    username: "sarah_manager",
    full_name: "Sarah Jenkins (Procurement Manager)",
    role: "MANAGER",
    is_active: true,
  },
  {
    id: 3,
    email: "mike.ops@freshmarket.com",
    username: "mike_ops",
    full_name: "Mike Miller (Inventory Operator)",
    role: "OPERATOR",
    is_active: true,
  },
  {
    id: 1,
    email: "admin@freshmarket.com",
    username: "admin",
    full_name: "System Administrator",
    role: "ADMIN",
    is_active: true,
  },
];

interface UserContextType {
  currentUser: User;
  switchUser: (user: User) => void;
  isManagerOrAdmin: boolean;
}

const UserContext = createContext<UserContextType | undefined>(undefined);

export const UserProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [currentUser, setCurrentUser] = useState<User>(PRESET_USERS[0]); // Default to Sarah Jenkins (Manager)

  useEffect(() => {
    const stored = localStorage.getItem("stockpilot_active_user");
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        const match = PRESET_USERS.find((u) => u.id === parsed.id) || parsed;
        setCurrentUser(match);
      } catch (e) {
        console.error("Failed to parse stored user", e);
      }
    } else {
      localStorage.setItem(
        "stockpilot_active_user",
        JSON.stringify(PRESET_USERS[0])
      );
    }
  }, []);

  const switchUser = (user: User) => {
    setCurrentUser(user);
    localStorage.setItem("stockpilot_active_user", JSON.stringify(user));
  };

  const isManagerOrAdmin =
    currentUser.role === "MANAGER" || currentUser.role === "ADMIN";

  return (
    <UserContext.Provider value={{ currentUser, switchUser, isManagerOrAdmin }}>
      {children}
    </UserContext.Provider>
  );
};

export const useUser = (): UserContextType => {
  const context = useContext(UserContext);
  if (!context) {
    throw new Error("useUser must be used within a UserProvider");
  }
  return context;
};
