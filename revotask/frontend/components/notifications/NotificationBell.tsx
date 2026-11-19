"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { BaseBadge } from "@/components/shared/BaseBadge";
import { BaseButton } from "@/components/shared/BaseButton";
import { useNotifications } from "@/hooks/useNotifications";
import type { Notification } from "@/types";

export function NotificationBell() {
  const router = useRouter();
  const { items, unread, markAsRead } = useNotifications();
  const [open, setOpen] = useState(false);

  const openNotification = async (n: Notification) => {
    if (!n.read_at) await markAsRead(n.id);
    setOpen(false);
    router.push(`/boards/${n.board_id}`);
  };

  return (
    <div className="relative">
      <BaseButton
        variant="secondary"
        aria-label={`Notifications, ${unread} unread`}
        aria-expanded={open}
        aria-haspopup="true"
        onClick={() => setOpen((v) => !v)}
      >
        <span aria-hidden="true">🔔</span>
        {unread > 0 && <BaseBadge tone="danger">{unread > 99 ? "99+" : unread}</BaseBadge>}
      </BaseButton>

      {open && (
        <div
          role="menu"
          className="absolute right-0 z-40 mt-2 w-80 max-w-[calc(100vw-2rem)] rounded-lg bg-white shadow-lg ring-1 ring-black/10"
        >
          {items.length === 0 ? (
            <p className="p-4 text-sm text-gray-500">No notifications</p>
          ) : (
            <ul className="max-h-96 divide-y divide-gray-100 overflow-y-auto">
              {items.map((n) => (
                <li key={n.id} role="none">
                  <BaseButton
                    variant="secondary"
                    role="menuitem"
                    onClick={() => openNotification(n)}
                    className={`w-full justify-start rounded-none text-left ring-0 ${
                      n.read_at ? "font-normal text-gray-500" : "bg-blue-50 font-semibold"
                    }`}
                  >
                    <span className="flex-1">
                      <span className="block">{n.message}</span>
                      <span className="block text-xs font-normal text-gray-500">
                        {new Date(n.created_at).toLocaleString()}
                      </span>
                    </span>
                  </BaseButton>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
