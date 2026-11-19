"use client";
import { memo, type DragEvent } from "react";
import { BaseBadge } from "@/components/shared/BaseBadge";
import type { Card } from "@/types";

type DragProps = {
  draggable: true;
  onDragStart: (e: DragEvent<HTMLElement>) => void;
  onDragEnd: () => void;
  [attr: string]: unknown;
};

interface KanbanCardProps {
  card: Card;
  dragProps: DragProps;
  dragging: boolean;
  dimmed: boolean;
  onOpen: (cardId: string) => void;
}

function KanbanCardBase({ card, dragProps, dragging, dimmed, onOpen }: KanbanCardProps) {
  const done = !!card.completed_at;
  return (
    <div
      {...dragProps}
      role="button"
      tabIndex={0}
      aria-label={`Open card ${card.title}`}
      onClick={() => onOpen(card.id)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onOpen(card.id);
        }
      }}
      className={`cursor-grab rounded-md bg-white p-3 shadow-sm ring-1 ring-black/5 hover:shadow ${
        dragging ? "opacity-40" : ""
      } ${dimmed ? "opacity-30" : ""}`}
    >
      <p className="break-words text-sm font-medium text-gray-900">{card.title}</p>
      <div className="mt-2 flex items-center justify-between gap-2 text-xs text-gray-500">
        <span className="truncate">{card.assignee ? card.assignee.name : "Unassigned"}</span>
        <BaseBadge tone={done ? "success" : "neutral"}>{done ? "Done" : "Open"}</BaseBadge>
      </div>
    </div>
  );
}

export const KanbanCard = memo(KanbanCardBase);
