"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { onAuthStateChanged, type User } from "firebase/auth";
import { auth } from "@/lib/firebase";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  loginAsDemo: () => void;
  logoutDemo: () => void;
}

export const DEMO_USER_OBJ = {
  uid: "demo_user_wardrobe",
  email: "demo@verdict.engine",
  displayName: "Verdict Demo Presenter",
} as unknown as User;

const AuthContext = createContext<AuthContextValue>({
  user: null,
  loading: true,
  loginAsDemo: () => {},
  logoutDemo: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const loginAsDemo = () => {
    localStorage.setItem("verdict_demo_token", "true");
    setUser(DEMO_USER_OBJ);
  };

  const logoutDemo = () => {
    localStorage.removeItem("verdict_demo_token");
    setUser(null);
  };

  useEffect(() => {
    const isDemo = typeof window !== "undefined" && localStorage.getItem("verdict_demo_token") === "true";
    if (isDemo) {
      setUser(DEMO_USER_OBJ);
      setLoading(false);
      return;
    }

    if (!auth) {
      setLoading(false);
      return;
    }
    const unsubscribe = onAuthStateChanged(auth, (firebaseUser) => {
      if (localStorage.getItem("verdict_demo_token") === "true") {
        setUser(DEMO_USER_OBJ);
      } else {
        setUser(firebaseUser);
      }
      setLoading(false);
    });
    return unsubscribe;
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, loginAsDemo, logoutDemo }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
