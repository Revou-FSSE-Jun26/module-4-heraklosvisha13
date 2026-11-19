"use client";
import { Suspense, useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { BoardAnalyticsPanel } from "@/components/boards/BoardAnalyticsPanel";
import { BoardMembersModal } from "@/components/boards/BoardMembersModal";
import { CardDetailModal } from "@/components/boards/CardDetailModal";
import { KanbanBoard } from "@/components/boards/KanbanBoard";
import { Navbar } from "@/components/layout/Navbar";
import { BaseBadge } from "@/components/shared/BaseBadge";
import { BaseButton } from "@/components/shared/BaseButton";
import { BaseModal } from "@/components/shared/BaseModal";
import { useAuth } from "@/context/AuthContext";
import type { ColumnWithCards } from "@/hooks/useDragAndDrop";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { useErrorHandler } from "@/hooks/useErrorHandler";
import { apiClient } from "@/lib/apiClient";
import type { BoardDetail, BoardMember, Card } from "@/types";

function BoardPageContent() {
  const { id: boardId } = useParams<{ id: string }>();
  const router = useRouter();
  const { status, token } = useAuth();
  const handleError = useErrorHandler();

  const [board, setBoard] = useState<BoardDetail | null>(null);
  const [columns, setColumns] = useState<ColumnWithCards[]>([]);
  const [members, setMembers] = useState<BoardMember[]>([]);
  const [selectedCardId, setSelectedCardId] = useState<string | null>(null);
  const [showAnalytics, setShowAnalytics] = useState(false);
  const [showMembers, setShowMembers] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const [searchQuery, setSearchQuery] = useState("");
  const debouncedQuery = useDebouncedValue(searchQuery.trim(), 300);
  const [result, setResult] = useState<{ q: string; ids: Set<string> } | null>(null);

  const isAdmin = board?.role === "admin";

  useEffect(() => {
    if (status === "unauthenticated") router.replace("/login");
  }, [status, router]);

  useEffect(() => {
    if (!token) return;
    let active = true;
    // The board must render even when the members request fails.
    apiClient<BoardDetail>(`/api/boards/${boardId}`, token)
      .then((b) => {
        if (!active) return;
        setBoard(b);
        setColumns(b.columns);
      })
      .catch((err) => {
        if (active) handleError(err);
      });
    apiClient<BoardMember[]>(`/api/boards/${boardId}/members`, token)
      .then((m) => {
        if (active) setMembers(m);
      })
      .catch(() => {
        // Non-fatal: the member list stays empty.
      });
    return () => {
      active = false;
    };
  }, [boardId, token, handleError]);

  // Debounced server-side search. Late responses are aborted.
  useEffect(() => {
    if (!token || !debouncedQuery) return;
    const controller = new AbortController();
    apiClient<Card[]>(`/api/boards/${boardId}/cards?q=${encodeURIComponent(debouncedQuery)}`, token, {
      signal: controller.signal,
    })
      .then((cards) => setResult({ q: debouncedQuery, ids: new Set(cards.map((c) => c.id)) }))
      .catch((err) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        handleError(err);
      });
    return () => controller.abort();
  }, [boardId, token, debouncedQuery, handleError]);

  // Everything is shown until results for the current query arrive.
  const matchIds = debouncedQuery && result?.q === debouncedQuery ? result.ids : null;
  const noMatches = matchIds !== null && matchIds.size === 0;

  const openCard = useCallback((cardId: string) => setSelectedCardId(cardId), []);
  const closeCard = useCallback(() => setSelectedCardId(null), []);

  const onCardUpdated = useCallback((card: Card) => {
    setColumns((prev) =>
      prev.map((col) =>
        col.cards.some((c) => c.id === card.id)
          ? { ...col, cards: col.cards.map((c) => (c.id === card.id ? { ...c, ...card } : c)) }
          : col,
      ),
    );
  }, []);

  const onCardDeleted = useCallback((cardId: string) => {
    setColumns((prev) =>
      prev.map((col) =>
        col.cards.some((c) => c.id === cardId) ? { ...col, cards: col.cards.filter((c) => c.id !== cardId) } : col,
      ),
    );
  }, []);

  const deleteBoard = async () => {
    setDeleting(true);
    try {
      await apiClient<{ id: string }>(`/api/boards/${boardId}`, token, { method: "DELETE" });
      router.replace("/");
    } catch (err) {
      handleError(err);
      setDeleting(false);
    }
  };

  if (status !== "authenticated") {
    return <p className="p-8 text-center text-gray-500">Loading…</p>;
  }

  return (
    <>
      <Navbar />
      <main className="mx-auto w-full max-w-6xl flex-1 p-4">
        {board === null ? (
          <p className="text-gray-500">Loading board…</p>
        ) : (
          <>
            <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-semibold text-gray-900">{board.name}</h1>
                <BaseBadge tone={isAdmin ? "success" : "neutral"}>{board.role}</BaseBadge>
              </div>
              {isAdmin && (
                <div className="flex flex-wrap gap-2">
                  <BaseButton variant="secondary" onClick={() => setShowAnalytics((v) => !v)}>
                    {showAnalytics ? "Hide analytics" : "Analytics"}
                  </BaseButton>
                  <BaseButton variant="secondary" onClick={() => setShowMembers(true)}>
                    Manage Members
                  </BaseButton>
                  <BaseButton variant="destructive" onClick={() => setConfirmDelete(true)}>
                    Delete Board
                  </BaseButton>
                </div>
              )}
            </div>

            {isAdmin && showAnalytics && <BoardAnalyticsPanel boardId={boardId} />}

            <label className="mb-4 block text-sm font-medium text-gray-700">
              Search cards
              <input
                type="search"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search by title or description"
                className="mt-1 block w-full max-w-md rounded-md border border-gray-300 px-3 py-2"
              />
            </label>
            {noMatches && <p className="mb-4 text-sm text-gray-500">No cards match your search.</p>}

            <KanbanBoard
              columns={columns}
              setColumns={setColumns}
              matchIds={matchIds}
              onOpenCard={openCard}
            />
          </>
        )}
      </main>

      {selectedCardId && (
        <CardDetailModal
          key={selectedCardId}
          cardId={selectedCardId}
          members={members}
          onClose={closeCard}
          onUpdated={onCardUpdated}
          onDeleted={onCardDeleted}
        />
      )}

      {isAdmin && (
        <>
          <BoardMembersModal
            boardId={boardId}
            isOpen={showMembers}
            members={members}
            onChange={setMembers}
            onClose={() => setShowMembers(false)}
          />
          <BaseModal
            isOpen={confirmDelete}
            title="Delete board?"
            onClose={() => setConfirmDelete(false)}
            footer={
              <>
                <BaseButton variant="secondary" onClick={() => setConfirmDelete(false)}>
                  Cancel
                </BaseButton>
                <BaseButton variant="destructive" loading={deleting} onClick={deleteBoard}>
                  Delete Board
                </BaseButton>
              </>
            }
          >
            <p className="text-sm text-gray-700">
              “{board?.name}” and all of its columns and cards will be removed.
            </p>
          </BaseModal>
        </>
      )}
    </>
  );
}

export default function BoardPage() {
  return (
    <Suspense fallback={<div className="p-6 text-sm text-gray-500">Loading board...</div>}>
      <BoardPageContent />
    </Suspense>
  );
}
