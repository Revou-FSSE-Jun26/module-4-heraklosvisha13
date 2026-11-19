"use client";
import { useState, type FormEvent } from "react";
import { BaseButton } from "@/components/shared/BaseButton";
import { BaseModal } from "@/components/shared/BaseModal";
import { useAuth } from "@/context/AuthContext";
import { useDragAndDrop, type ColumnWithCards } from "@/hooks/useDragAndDrop";
import { useErrorHandler } from "@/hooks/useErrorHandler";
import { apiClient } from "@/lib/apiClient";
import type { Card } from "@/types";
import { KanbanColumn } from "./KanbanColumn";

interface KanbanBoardProps {
  columns: ColumnWithCards[];
  setColumns: (next: ColumnWithCards[]) => void;
  matchIds: Set<string> | null;
  onOpenCard: (cardId: string) => void;
}

export function KanbanBoard({ columns, setColumns, matchIds, onOpenCard }: KanbanBoardProps) {
  const { token } = useAuth();
  const handleError = useErrorHandler();
  const { draggingId, overColumnId, getCardProps, getColumnProps } = useDragAndDrop(columns, setColumns);
  const [addTo, setAddTo] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [saving, setSaving] = useState(false);

  const closeAdd = () => {
    setAddTo(null);
    setTitle("");
  };

  const createCard = async (e: FormEvent) => {
    e.preventDefault();
    if (!addTo) return;
    setSaving(true);
    try {
      const card = await apiClient<Card>(`/api/columns/${addTo}/cards`, token, {
        method: "POST",
        body: JSON.stringify({ title: title.trim() }),
      });
      setColumns(columns.map((c) => (c.id === addTo ? { ...c, cards: [...c.cards, card] } : c)));
      closeAdd();
    } catch (err) {
      handleError(err);
    } finally {
      setSaving(false);
    }
  };

  if (columns.length === 0) {
    return <p className="text-gray-500">This board has no columns yet.</p>;
  }

  return (
    <>
      <div className="flex gap-4 overflow-x-auto pb-4">
        {columns.map((column) => (
          <KanbanColumn
            key={column.id}
            column={column}
            columnProps={getColumnProps(column)}
            getCardProps={getCardProps}
            draggingId={draggingId}
            isOver={overColumnId === column.id}
            matchIds={matchIds}
            onOpenCard={onOpenCard}
            onAddCard={setAddTo}
          />
        ))}
      </div>
      <BaseModal
        isOpen={addTo !== null}
        title="New card"
        onClose={closeAdd}
        footer={
          <>
            <BaseButton variant="secondary" onClick={closeAdd}>
              Cancel
            </BaseButton>
            <BaseButton type="submit" form="create-card-form" loading={saving} disabled={!title.trim()}>
              Create
            </BaseButton>
          </>
        }
      >
        <form id="create-card-form" onSubmit={createCard}>
          <label className="block text-sm font-medium text-gray-700">
            Title
            <input
              required
              maxLength={200}
              autoFocus
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2"
            />
          </label>
        </form>
      </BaseModal>
    </>
  );
}
