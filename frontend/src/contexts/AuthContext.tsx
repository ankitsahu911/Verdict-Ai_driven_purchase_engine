"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { onAuthStateChanged, type User } from "firebase/auth";
import { auth } from "@/lib/firebase";

export interface AuthUser {
  uid: string;
  email: string;
  displayName: string;
}

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  loginAsDemo: () => void;
  loginWithEmail: (email: string, password: string) => Promise<boolean>;
  registerWithEmail: (email: string, password: string, name?: string) => Promise<boolean>;
  logout: () => void;
}

export const DEMO_USER_OBJ: AuthUser = {
  uid: "demo_user_wardrobe",
  email: "anknk@verdict.ai",
  displayName: "Verdict Curator",
};

const AuthContext = createContext<AuthContextValue>({
  user: null,
  loading: true,
  loginAsDemo: () => {},
  loginWithEmail: async () => false,
  registerWithEmail: async () => false,
  logout: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  const loginAsDemo = () => {
    localStorage.setItem("verdict_demo_token", "true");
    localStorage.setItem("verdict_auth_user", JSON.stringify(DEMO_USER_OBJ));
    setUser(DEMO_USER_OBJ);
  };

  const loginWithEmail = async (email: string, password: string): Promise<boolean> => {
    if (!email || !password) return false;
    // Check locally registered users or create user session
    const storedUsersRaw = localStorage.getItem("verdict_registered_users");
    const storedUsers: Record<string, { email: string; password: string; name: string }> = storedUsersRaw
      ? JSON.parse(storedUsersRaw)
      : {};

    let displayName = email.split("@")[0];
    if (storedUsers[email.toLowerCase()]) {
      displayName = storedUsers[email.toLowerCase()].name;
    } else {
      // Auto-register account for seamless access
      storedUsers[email.toLowerCase()] = { email, password, name: displayName };
      localStorage.setItem("verdict_registered_users", JSON.stringify(storedUsers));
    }

    const authUser: AuthUser = {
      uid: `user_${email.replace(/[^a-zA-Z0-9]/g, "_")}`,
      email: email.trim(),
      displayName,
    };

    localStorage.setItem("verdict_demo_token", "true");
    localStorage.setItem("verdict_auth_user", JSON.stringify(authUser));
    setUser(authUser);
    return true;
  };

  const registerWithEmail = async (email: string, password: string, name?: string): Promise<boolean> => {
    if (!email || !password) return false;
    const storedUsersRaw = localStorage.getItem("verdict_registered_users");
    const storedUsers = storedUsersRaw ? JSON.parse(storedUsersRaw) : {};
    const displayName = name || email.split("@")[0];
    storedUsers[email.toLowerCase()] = { email, password, name: displayName };
    localStorage.setItem("verdict_registered_users", JSON.stringify(storedUsers));

    const authUser: AuthUser = {
      uid: `user_${email.replace(/[^a-zA-Z0-9]/g, "_")}`,
      email: email.trim(),
      displayName,
    };
    localStorage.setItem("verdict_demo_token", "true");
    localStorage.setItem("verdict_auth_user", JSON.stringify(authUser));
    setUser(authUser);
    return true;
  };

  const logout = () => {
    localStorage.removeItem("verdict_demo_token");
    localStorage.removeItem("verdict_auth_user");
    setUser(null);
  };

  useEffect(() => {
    try {
      const stored = localStorage.getItem("verdict_auth_user");
      if (stored) {
        setUser(JSON.parse(stored));
      } else if (localStorage.getItem("verdict_demo_token") === "true") {
        setUser(DEMO_USER_OBJ);
      }
    } catch {
      // fallback
    } finally {
      setLoading(false);
    }
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        loginAsDemo,
        loginWithEmail,
        registerWithEmail,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
