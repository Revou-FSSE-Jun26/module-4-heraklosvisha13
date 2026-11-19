"use client";
import { memo, type DragEvent } from "react";
import { BaseButton } from "@/components/shared/BaseButton";
import type { ColumnWithCards } from "@/hooks/useDragAndDrop";
import type { Card } from "@/types";
import { KanbanCard } from "./KanbanCard";

type CardDragProps = Parameters<typeof KanbanCard>[0]["dragProps"];
type ColumnDragProps = {
  onDragOver: (e: DragEvent<HTMLElement>) => void;
  onDragLeave: (e: DragEvent<HTMLElement>) => void;
  onDrop: (e: DragEvent<HTMLElement>) => void;
};

interface KanbanColumnProps {
  column: ColumnWithCards;
  columnProps: ColumnDragProps;
  getCardProps: (card: Card) => CardDragProps;
  draggingId: string | null;
  isOver: boolean;
  matchIds: Set<string> | null;
  onOpenCard: (cardId: string) => void;
  onAddCard: (columnId: string) => void;
}

function KanbanColumnBase({
  column,
  columnProps,
  getCardProps,
  draggingId,
  isOver,
  matchIds,
  onOpenCard,
  onAddCard,
}: KanbanColumnProps) {
  return (
    <section
      {...columnProps}
      aria-label={column.name}
      className={`flex w-72 shrink-0 flex-col rounded-lg bg-gray-100 p-3 ${
        isOver ? "ring-2 ring-blue-400" : ""
      }`}
    >
      <h2 className="mb-3 flex items-center justify-between text-sm font-semibold text-gray-800">
        <span className="truncate">{column.name}</span>
        <span className="text-xs font-normal text-gray-500">{column.cards.length}</span>
      </h2>
      <div className="flex min-h-12 flex-1 flex-col gap-2">
        {column.cards.map((card) => (
          <KanbanCard
            key={card.id}
            card={card}
            dragProps={getCardProps(card)}
            dragging={draggingId === card.id}
            dimmed={matchIds !== null && !matchIds.has(card.id)}
            onOpen={onOpenCard}
          />
        ))}
      </div>
      <BaseButton variant="secondary" className="mt-3" onClick={() => onAddCard(column.id)}>
        Add card
      </BaseButton>
    </section>
  );
}

export const KanbanColumn = memo(KanbanColumnBase);
