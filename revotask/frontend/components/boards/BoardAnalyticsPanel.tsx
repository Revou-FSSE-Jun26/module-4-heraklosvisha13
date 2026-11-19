"use client";
import { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { useErrorHandler } from "@/hooks/useErrorHandler";
import { apiClient } from "@/lib/apiClient";
import type { BoardAnalytics } from "@/types";

/** Render only for board admins; the endpoint returns 403 otherwise. */
export function BoardAnalyticsPanel({ boardId }: { boardId: string }) {
  const { token } = useAuth();
  const handleError = useErrorHandler();
  const [data, setData] = useState<BoardAnalytics | null>(null);

  useEffect(() => {
    if (!token) return;
    let active = true;
    apiClient<BoardAnalytics>(`/api/boards/${boardId}/analytics`, token)
      .then((res) => {
        if (active) setData(res);
      })
      .catch((err) => {
        if (active) handleError(err);
      });
    return () => {
      active = false;
    };
  }, [boardId, token, handleError]);

  if (!data) return <p className="text-sm text-gray-500">Loading analytics…</p>;

  const max = Math.max(1, ...data.cards_per_column.map((c) => c.count));
  return (
    <section aria-label="Board analytics" className="mb-4 space-y-4 rounded-lg bg-white p-4 shadow ring-1 ring-black/5">
      <div className="flex items-baseline justify-between gap-2">
        <h2 className="text-lg font-semibold text-gray-900">Analytics</h2>
        <p className="text-sm text-gray-600">
          Completed this week: <strong>{data.completed_this_week.count}</strong>
        </p>
      </div>
      <div>
        <h3 className="mb-2 text-sm font-medium text-gray-700">Cards per column</h3>
        <ul className="space-y-1">
          {data.cards_per_column.map((c) => (
            <li key={c.column_id} className="flex items-center gap-2 text-sm">
              <span className="w-28 truncate text-gray-700">{c.name}</span>
              <div className="h-3 flex-1 rounded bg-gray-100">
                <div className="h-3 rounded bg-blue-500" style={{ width: `${(c.count / max) * 100}%` }} />
              </div>
              <span className="w-6 text-right text-gray-600">{c.count}</span>
            </li>
          ))}
        </ul>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="text-gray-500">
            <tr>
              <th className="py-1 pr-4 font-medium">Member</th>
              <th className="py-1 pr-4 font-medium">Assigned</th>
              <th className="py-1 pr-4 font-medium">Completed this week</th>
              <th className="py-1 font-medium">Comments</th>
            </tr>
          </thead>
          <tbody>
            {data.member_activity.map((m) => (
              <tr key={m.user_id} className="border-t border-gray-100">
                <td className="py-1 pr-4 text-gray-900">{m.name}</td>
                <td className="py-1 pr-4">{m.assigned_count}</td>
                <td className="py-1 pr-4">{m.completed_this_week}</td>
                <td className="py-1">{m.comments_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
