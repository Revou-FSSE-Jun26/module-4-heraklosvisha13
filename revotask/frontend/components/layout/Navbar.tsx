"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { BaseButton } from "@/components/shared/BaseButton";
import { NotificationBell } from "@/components/notifications/NotificationBell";
import { useAuth } from "@/context/AuthContext";

export function Navbar() {
  const router = useRouter();
  const { user, logout } = useAuth();

  return (
    <header className="border-b border-gray-200 bg-white">
      <nav className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2 px-4 py-2">
        <Link href="/" className="text-lg font-semibold text-gray-900">
          RevoTask
        </Link>
        <div className="flex items-center gap-2">
          <BaseButton variant="secondary" onClick={() => router.push("/")}>
            Boards
          </BaseButton>
          <BaseButton variant="secondary" onClick={() => router.push("/my-tasks")}>
            My tasks
          </BaseButton>
          <BaseButton variant="secondary" onClick={() => router.push("/profile")}>
            Profile
          </BaseButton>
          <NotificationBell />
          {user && <span className="hidden text-sm text-gray-700 sm:inline">{user.name}</span>}
          <BaseButton variant="destructive" onClick={logout}>
            Logout
          </BaseButton>
        </div>
      </nav>
    </header>
  );
}
