"use client";
import { useState, type FormEvent } from "react";
import { BaseBadge } from "@/components/shared/BaseBadge";
import { BaseButton } from "@/components/shared/BaseButton";
import { BaseModal } from "@/components/shared/BaseModal";
import { useAuth } from "@/context/AuthContext";
import { useErrorHandler } from "@/hooks/useErrorHandler";
import { apiClient } from "@/lib/apiClient";
import type { BoardMember, Role } from "@/types";

interface BoardMembersModalProps {
  boardId: string;
  isOpen: boolean;
  members: BoardMember[];
  onChange: (members: BoardMember[]) => void;
  onClose: () => void;
}

/** Admin-only: the page renders it only when the board role is `admin`. */
export function BoardMembersModal({ boardId, isOpen, members, onChange, onClose }: BoardMembersModalProps) {
  const { token, user } = useAuth();
  const handleError = useErrorHandler();
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<Role>("member");
  const [adding, setAdding] = useState(false);

  const add = async (e: FormEvent) => {
    e.preventDefault();
    setAdding(true);
    try {
      const member = await apiClient<BoardMember>(`/api/boards/${boardId}/members`, token, {
        method: "POST",
        body: JSON.stringify({ email: email.trim(), role }),
      });
      onChange([...members, member]);
      setEmail("");
      setRole("member");
    } catch (err) {
      handleError(err);
    } finally {
      setAdding(false);
    }
  };

  const changeRole = async (userId: string, next: Role) => {
    try {
      const updated = await apiClient<BoardMember>(`/api/boards/${boardId}/members/${userId}`, token, {
        method: "PATCH",
        body: JSON.stringify({ role: next }),
      });
      onChange(members.map((m) => (m.user_id === userId ? updated : m)));
    } catch (err) {
      handleError(err);
    }
  };

  const remove = async (userId: string) => {
    try {
      await apiClient<{ id: string }>(`/api/boards/${boardId}/members/${userId}`, token, {
        method: "DELETE",
      });
      onChange(members.filter((m) => m.user_id !== userId));
    } catch (err) {
      handleError(err);
    }
  };

  return (
    <BaseModal isOpen={isOpen} title="Manage members" onClose={onClose}>
      <ul className="mb-4 space-y-2">
        {members.map((m) => (
          <li key={m.user_id} className="flex flex-wrap items-center justify-between gap-2 text-sm">
            <div className="min-w-0">
              <p className="truncate font-medium text-gray-900">{m.name}</p>
              <p className="truncate text-gray-500">{m.email}</p>
            </div>
            <div className="flex items-center gap-2">
              <BaseBadge tone={m.role === "admin" ? "success" : "neutral"}>{m.role}</BaseBadge>
              {m.user_id !== user?.id && (
                <>
                  <BaseButton
                    variant="secondary"
                    onClick={() => changeRole(m.user_id, m.role === "admin" ? "member" : "admin")}
                  >
                    Make {m.role === "admin" ? "member" : "admin"}
                  </BaseButton>
                  <BaseButton variant="destructive" onClick={() => remove(m.user_id)}>
                    Remove
                  </BaseButton>
                </>
              )}
            </div>
          </li>
        ))}
      </ul>
      <form onSubmit={add} className="space-y-3 border-t border-gray-200 pt-4">
        <label className="block text-sm font-medium text-gray-700">
          Email
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2"
          />
        </label>
        <label className="block text-sm font-medium text-gray-700">
          Role
          <select
            value={role}
            onChange={(e) => setRole(e.target.value as Role)}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2"
          >
            <option value="member">member</option>
            <option value="admin">admin</option>
          </select>
        </label>
        <div className="flex justify-end">
          <BaseButton type="submit" loading={adding} disabled={!email.trim()}>
            Add member
          </BaseButton>
        </div>
      </form>
    </BaseModal>
  );
}
