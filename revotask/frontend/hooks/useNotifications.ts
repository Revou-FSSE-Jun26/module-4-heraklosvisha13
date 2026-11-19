"use client";
import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { apiClient } from "@/lib/apiClient";
import { useErrorHandler } from "@/hooks/useErrorHandler";
import type { Notification } from "@/types";

export const POLL_MS = 30_000;

export interface NotificationPage {
  items: Notification[];
  page: number;
  per_page: number;
  total: number;
  pages: number;
  unread_count: number;
}

/**
 * Loads notifications on mount and every 30 s. The effect owns exactly one
 * interval; it is cleared on unmount, on logout (token becomes null) and on
 * token change. Mount this hook once (e.g. in a provider) to keep one timer.
 */
export function useNotifications() {
  const { token } = useAuth();
  const handleError = useErrorHandler();
  const [page, setPage] = useState<NotificationPage | null>(null);

  useEffect(() => {
    if (!token) {
      // No session: nothing to poll, drop stale data.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setPage(null);
      return;
    }
    let active = true;
    const load = () =>
      apiClient<NotificationPage>("/api/notifications?page=1&per_page=20", token)
        .then((res) => {
          if (active) setPage(res);
        })
        .catch(() => {
          // A failed poll shows no toast and does not stop polling.
        });
    load();
    const id = setInterval(load, POLL_MS);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, [token]);

  const markAsRead = useCallback(
    async (id: string) => {
      try {
        const updated = await apiClient<Notification>(`/api/notifications/${id}/read`, token, {
          method: "PATCH",
        });
        setPage((prev) => {
          if (!prev) return prev;
          const target = prev.items.find((n) => n.id === id);
          const wasUnread = !!target && target.read_at === null;
          return {
            ...prev,
            items: prev.items.map((n) => (n.id === id ? { ...n, read_at: updated.read_at } : n)),
            unread_count: wasUnread ? Math.max(0, prev.unread_count - 1) : prev.unread_count,
          };
        });
      } catch (err) {
        handleError(err);
      }
    },
    [token, handleError],
  );

  return { items: page?.items ?? [], unread: page?.unread_count ?? 0, markAsRead };
}
