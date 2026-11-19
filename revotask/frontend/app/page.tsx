"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Navbar } from "@/components/layout/Navbar";
import { BaseBadge } from "@/components/shared/BaseBadge";
import { BaseButton } from "@/components/shared/BaseButton";
import { BaseModal } from "@/components/shared/BaseModal";
import { useAuth } from "@/context/AuthContext";
import { useErrorHandler } from "@/hooks/useErrorHandler";
import { apiClient } from "@/lib/apiClient";
import type { Board } from "@/types";

export default function DashboardPage() {
  const router = useRouter();
  const { status, token } = useAuth();
  const handleError = useErrorHandler();
  const [boards, setBoards] = useState<Board[] | null>(null);
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (status === "unauthenticated") router.replace("/login");
  }, [status, router]);

  useEffect(() => {
    if (!token) return;
    let active = true;
    apiClient<Board[]>("/api/boards", token)
      .then((res) => {
        if (active) setBoards(res);
      })
      .catch((err) => {
        if (active) handleError(err);
      });
    return () => {
      active = false;
    };
  }, [token, handleError]);

  const closeModal = useCallback(() => {
    setOpen(false);
    setName("");
  }, []);

  const createBoard = async (e: FormEvent) => {
    e.preventDefault();
    setCreating(true);
    try {
      const board = await apiClient<Board>("/api/boards", token, {
        method: "POST",
        body: JSON.stringify({ name: name.trim() }),
      });
      setBoards((prev) => [board, ...(prev ?? [])]);
      closeModal();
    } catch (err) {
      handleError(err);
    } finally {
      setCreating(false);
    }
  };

  if (status !== "authenticated") {
    return <p className="p-8 text-center text-gray-500">Loading…</p>;
  }

  return (
    <>
      <Navbar />
      <main className="mx-auto w-full max-w-6xl flex-1 p-4">
        <div className="mb-4 flex items-center justify-between gap-2">
          <h1 className="text-2xl font-semibold text-gray-900">Your boards</h1>
          <BaseButton onClick={() => setOpen(true)}>Create Board</BaseButton>
        </div>

        {boards === null ? (
          <p className="text-gray-500">Loading boards…</p>
        ) : boards.length === 0 ? (
          <p className="text-gray-500">You have no boards yet. Create your first one.</p>
        ) : (
          <ul className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {boards.map((b) => (
              <li key={b.id}>
                <Link
                  href={`/boards/${b.id}`}
                  className="block rounded-lg bg-white p-4 shadow ring-1 ring-black/5 transition hover:shadow-md"
                >
                  <h2 className="truncate text-lg font-medium text-gray-900">{b.name}</h2>
                  <div className="mt-2 flex items-center justify-between text-sm text-gray-500">
                    <BaseBadge tone={b.role === "admin" ? "success" : "neutral"}>{b.role}</BaseBadge>
                    <span>{new Date(b.created_at).toLocaleDateString()}</span>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </main>

      <BaseModal
        isOpen={open}
        title="Create Board"
        onClose={closeModal}
        footer={
          <>
            <BaseButton variant="secondary" onClick={closeModal}>
              Cancel
            </BaseButton>
            <BaseButton type="submit" form="create-board-form" loading={creating} disabled={!name.trim()}>
              Create
            </BaseButton>
          </>
        }
      >
        <form id="create-board-form" onSubmit={createBoard}>
          <label className="block text-sm font-medium text-gray-700">
            Board name
            <input
              required
              maxLength={120}
              autoFocus
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2"
            />
          </label>
        </form>
      </BaseModal>
    </>
  );
}
