"use client";
import { useCallback, useEffect, useRef, useState, type DragEvent } from "react";
import { useAuth } from "@/context/AuthContext";
import { apiClient } from "@/lib/apiClient";
import { computeOrder } from "@/lib/ordering";
import { useErrorHandler } from "@/hooks/useErrorHandler";
import type { Card, Column } from "@/types";

export type ColumnWithCards = Column & { cards: Card[] };
type Rebalanced = { rebalanced: { id: string; order: number }[] };

const CARD_ATTR = "data-card-id";

function moveCardLocally(
  columns: ColumnWithCards[],
  cardId: string,
  columnId: string,
  index: number,
  order: number,
): ColumnWithCards[] {
  const moved = columns.flatMap((c) => c.cards).find((c) => c.id === cardId);
  if (!moved) return columns;
  return columns.map((col) => {
    const hasCard = col.cards.some((c) => c.id === cardId);
    if (col.id !== columnId && !hasCard) return col; // keep by reference
    const rest = col.cards.filter((c) => c.id !== cardId);
    if (col.id !== columnId) return { ...col, cards: rest };
    const next = [...rest];
    next.splice(index, 0, { ...moved, column_id: columnId, order });
    return { ...col, cards: next };
  });
}

function applyServerCard(columns: ColumnWithCards[], res: Card & Rebalanced): ColumnWithCards[] {
  const orders = new Map(res.rebalanced.map((r) => [r.id, r.order]));
  return columns.map((col) => {
    if (!col.cards.some((c) => c.id === res.id || orders.has(c.id))) return col;
    return {
      ...col,
      cards: col.cards.map((c) => {
        if (c.id === res.id) {
          const { rebalanced: _unused, ...card } = res;
          void _unused;
          return { ...c, ...card, order: orders.get(c.id) ?? card.order };
        }
        return orders.has(c.id) ? { ...c, order: orders.get(c.id)! } : c;
      }),
    };
  });
}

/** Insertion index among the column's cards (dragged card excluded), from pointer Y. */
function insertionIndex(container: HTMLElement, draggedId: string, clientY: number): number {
  const els = Array.from(container.querySelectorAll<HTMLElement>(`[${CARD_ATTR}]`)).filter(
    (el) => el.getAttribute(CARD_ATTR) !== draggedId,
  );
  let index = 0;
  for (const el of els) {
    const rect = el.getBoundingClientRect();
    if (clientY > rect.top + rect.height / 2) index += 1;
  }
  return index;
}

export function useDragAndDrop(
  columns: ColumnWithCards[],
  setColumns: (next: ColumnWithCards[]) => void,
) {
  const { token } = useAuth();
  const handleError = useErrorHandler();
  const columnsRef = useRef(columns); // latest state, avoids stale closures
  useEffect(() => {
    columnsRef.current = columns;
  }, [columns]);
  const [draggingId, setDraggingId] = useState<string | null>(null);
  const [overColumnId, setOverColumnId] = useState<string | null>(null);

  const drop = useCallback(
    async (cardId: string, columnId: string, index: number) => {
      const snapshot = columnsRef.current;
      const target = snapshot.find((c) => c.id === columnId);
      if (!target) return;
      const siblings = target.cards.filter((c) => c.id !== cardId);
      const currentIndex = target.cards.findIndex((c) => c.id === cardId);
      if (currentIndex === index) return; // dropped where it already is
      const order = computeOrder(siblings, index);
      setColumns(moveCardLocally(snapshot, cardId, columnId, index, order)); // optimistic
      try {
        const res = await apiClient<Card & Rebalanced>(`/api/cards/${cardId}/position`, token, {
          method: "PATCH",
          body: JSON.stringify({ column_id: columnId, order }),
        });
        setColumns(applyServerCard(columnsRef.current, res));
      } catch (err) {
        setColumns(snapshot); // rollback
        handleError(err);
      }
    },
    [token, setColumns, handleError],
  );

  const getCardProps = useCallback(
    (card: Card) => ({
      draggable: true as const,
      [CARD_ATTR]: card.id,
      onDragStart: (e: DragEvent<HTMLElement>) => {
        e.dataTransfer.setData("text/plain", card.id);
        e.dataTransfer.effectAllowed = "move";
        setDraggingId(card.id);
      },
      onDragEnd: () => {
        setDraggingId(null);
        setOverColumnId(null);
      },
    }),
    [],
  );

  const getColumnProps = useCallback(
    (column: ColumnWithCards) => ({
      onDragOver: (e: DragEvent<HTMLElement>) => {
        e.preventDefault(); // required to allow a drop
        e.dataTransfer.dropEffect = "move";
        setOverColumnId(column.id);
      },
      onDragLeave: (e: DragEvent<HTMLElement>) => {
        if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setOverColumnId(null);
      },
      onDrop: (e: DragEvent<HTMLElement>) => {
        e.preventDefault();
        const cardId = e.dataTransfer.getData("text/plain") || draggingId;
        setDraggingId(null);
        setOverColumnId(null);
        if (!cardId) return;
        void drop(cardId, column.id, insertionIndex(e.currentTarget, cardId, e.clientY));
      },
    }),
    [draggingId, drop],
  );

  return { draggingId, overColumnId, getCardProps, getColumnProps };
}
