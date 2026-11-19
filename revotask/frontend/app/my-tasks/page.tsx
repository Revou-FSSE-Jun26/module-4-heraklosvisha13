"use client";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Navbar } from "@/components/layout/Navbar";
import { BaseBadge } from "@/components/shared/BaseBadge";
import { BaseButton } from "@/components/shared/BaseButton";
import { useAuth } from "@/context/AuthContext";
import { useErrorHandler } from "@/hooks/useErrorHandler";
import { apiClient } from "@/lib/apiClient";
import type { TaskItem, TaskList } from "@/types";

export default function MyTasksPage() {
  const router = useRouter();
  const { status, token } = useAuth();
  const handleError = useErrorHandler();
  const [tasks, setTasks] = useState<TaskList | null>(null);

  useEffect(() => {
    if (status === "unauthenticated") router.replace("/login");
  }, [status, router]);

  useEffect(() => {
    if (!token) return;
    let active = true;
    apiClient<TaskList>("/api/cards?assignee=me", token)
      .then((res) => {
        if (active) setTasks(res);
      })
      .catch((err) => {
        if (active) handleError(err);
      });
    return () => {
      active = false;
    };
  }, [token, handleError]);

  const groups = useMemo(() => {
    const map = new Map<string, { boardId: string; name: string; items: TaskItem[] }>();
    for (const t of tasks?.items ?? []) {
      const g = map.get(t.board_id) ?? { boardId: t.board_id, name: t.board_name, items: [] };
      g.items.push(t);
      map.set(t.board_id, g);
    }
    return Array.from(map.values());
  }, [tasks]);

  if (status !== "authenticated") {
    return <p className="p-8 text-center text-gray-500">Loading…</p>;
  }

  return (
    <>
      <Navbar />
      <main className="mx-auto w-full max-w-3xl flex-1 p-4">
        <h1 className="mb-4 text-2xl font-semibold text-gray-900">My tasks</h1>
        {tasks === null ? (
          <p className="text-gray-500">Loading tasks…</p>
        ) : (
          <>
            <div className="mb-6 flex flex-wrap gap-2" aria-label="Progress summary">
              <BaseBadge>Total: {tasks.total}</BaseBadge>
              <BaseBadge tone="success">Completed: {tasks.completed}</BaseBadge>
              <BaseBadge tone="warning">Open: {tasks.open}</BaseBadge>
            </div>
            {groups.length === 0 ? (
              <p className="text-gray-500">No cards are assigned to you.</p>
            ) : (
              <div className="space-y-6">
                {groups.map((g) => (
                  <section key={g.boardId} aria-label={g.name}>
                    <h2 className="mb-2 text-lg font-medium text-gray-900">{g.name}</h2>
                    <ul className="space-y-2">
                      {g.items.map((t) => (
                        <li
                          key={t.id}
                          className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-white p-3 shadow ring-1 ring-black/5"
                        >
                          <div className="min-w-0">
                            <p className="truncate font-medium text-gray-900">{t.title}</p>
                            <p className="text-xs text-gray-500">
                              {t.column_name}
                              {t.due_date ? ` · Due ${new Date(t.due_date).toLocaleDateString()}` : ""}
                            </p>
                          </div>
                          <div className="flex items-center gap-2">
                            <BaseBadge tone={t.completed_at ? "success" : "warning"}>
                              {t.completed_at ? "Done" : "Open"}
                            </BaseBadge>
                            <BaseButton
                              variant="secondary"
                              onClick={() => router.push(`/boards/${t.board_id}`)}
                            >
                              Open board
                            </BaseButton>
                          </div>
                        </li>
                      ))}
                    </ul>
                  </section>
                ))}
              </div>
            )}
          </>
        )}
      </main>
    </>
  );
}
