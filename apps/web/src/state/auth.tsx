import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import { api } from "../lib/api";

export interface AuthUser {
  id: string;
  email: string;
  name: string;
  plan: string;
}

interface AuthState {
  user: AuthUser | null;
  token: string | null;
  demoMode: boolean;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (name: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(() => localStorage.getItem("ip_token"));
  const [demoMode, setDemoMode] = useState(true);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const data = await api.get<{ user: AuthUser }>("/api/auth/me", token);
      setUser(data.user);
      const health = await api.get<{ demoMode: boolean }>("/api/health");
      setDemoMode(health.demoMode);
    } catch {
      localStorage.removeItem("ip_token");
      setToken(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const value = useMemo<AuthState>(
    () => ({
      user,
      token,
      demoMode,
      loading,
      async login(email, password) {
        const data = await api.post<{ user: AuthUser; token: string; demoMode: boolean }>("/api/auth/login", {
          email,
          password,
        });
        localStorage.setItem("ip_token", data.token);
        setToken(data.token);
        setUser(data.user);
        setDemoMode(data.demoMode);
      },
      async signup(name, email, password) {
        const data = await api.post<{ user: AuthUser; token: string; demoMode: boolean }>("/api/auth/signup", {
          name,
          email,
          password,
        });
        localStorage.setItem("ip_token", data.token);
        setToken(data.token);
        setUser(data.user);
        setDemoMode(data.demoMode);
      },
      async logout() {
        try {
          if (token) await api.post("/api/auth/logout", {}, token);
        } catch {
          /* ignore */
        }
        localStorage.removeItem("ip_token");
        setToken(null);
        setUser(null);
      },
      refresh,
    }),
    [user, token, demoMode, loading]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
