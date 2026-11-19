"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";
import { apiClient } from "@/lib/apiClient";
import { ApiError } from "@/lib/errors";
import type { User, UserPublic } from "@/types";

const TOKEN_KEY = "revotask.token";
const COOKIE_NAME = "revotask_token";
const DEFAULT_MAX_AGE = 60 * 60 * 24;

type AuthState = {
  status: "loading" | "authenticated" | "unauthenticated";
  token: string | null;
  user: User | UserPublic | null;
  login: (token: string, user: UserPublic) => void;
  logout: () => void;
  setUser: (user: User) => void;
};

const AuthContext = createContext<AuthState | null>(null);

/** Seconds until the JWT expires, so the cookie lives as long as the token. */
function tokenMaxAge(token: string): number {
  try {
    const payload = JSON.parse(atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")));
    const left = Math.floor(payload.exp - Date.now() / 1000);
    if (Number.isFinite(left) && left > 0) return left;
  } catch {
    // fall through to the default
  }
  return DEFAULT_MAX_AGE;
}

function writeCookie(token: string) {
  document.cookie = `${COOKIE_NAME}=${encodeURIComponent(token)}; path=/; SameSite=Lax; Max-Age=${tokenMaxAge(token)}`;
}

function clearCookie() {
  document.cookie = `${COOKIE_NAME}=; path=/; SameSite=Lax; Max-Age=0`;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [user, setUserState] = useState<User | UserPublic | null>(null);
  const [status, setStatus] = useState<AuthState["status"]>("loading");

  const clearSession = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    clearCookie();
    setToken(null);
    setUserState(null);
    setStatus("unauthenticated");
  }, []);

  const logout = useCallback(() => {
    clearSession();
    router.replace("/login");
  }, [clearSession, router]);

  const login = useCallback(
    (newToken: string, newUser: UserPublic) => {
      localStorage.setItem(TOKEN_KEY, newToken);
      writeCookie(newToken);
      setToken(newToken);
      setUserState(newUser);
      setStatus("authenticated");
      router.replace("/");
    },
    [router],
  );

  const setUser = useCallback((next: User) => setUserState(next), []);

  // Restore the session on mount; localStorage is the source of truth.
  useEffect(() => {
    const stored = localStorage.getItem(TOKEN_KEY);
    if (!stored) {
      // localStorage is unavailable during SSR, so it can only be read after mount.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setStatus("unauthenticated");
      return;
    }
    writeCookie(stored); // re-sync so Server Components can read it
    setToken(stored);
    setStatus("authenticated");
    let cancelled = false;
    apiClient<User>("/api/users/me", stored)
      .then((me) => {
        if (!cancelled) setUserState(me);
      })
      .catch((err) => {
        if (!cancelled && err instanceof ApiError && err.status === 401) logout();
      });
    return () => {
      cancelled = true;
    };
    // Runs once on mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const value = useMemo(
    () => ({ status, token, user, login, logout, setUser }),
    [status, token, user, login, logout, setUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
