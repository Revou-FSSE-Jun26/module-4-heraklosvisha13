"use client";
import { useEffect, useState, type FormEvent } from "react";
import toast from "react-hot-toast";
import { BaseBadge } from "@/components/shared/BaseBadge";
import { BaseButton } from "@/components/shared/BaseButton";
import { BaseModal } from "@/components/shared/BaseModal";
import { useAuth } from "@/context/AuthContext";
import { useErrorHandler } from "@/hooks/useErrorHandler";
import { apiClient } from "@/lib/apiClient";
import type { Card, CardDetail, Comment, BoardMember } from "@/types";

interface CardDetailModalProps {
  cardId: string;
  members: BoardMember[];
  onClose: () => void;
  onUpdated: (card: Card) => void;
  onDeleted: (cardId: string) => void;
}

const FIELD = "mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm";

/** Mount with `key={cardId}` so state resets when another card opens. */
export function CardDetailModal({ cardId, members, onClose, onUpdated, onDeleted }: CardDetailModalProps) {
  const { token, user } = useAuth();
  const handleError = useErrorHandler();
  const [card, setCard] = useState<CardDetail | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [assigneeId, setAssigneeId] = useState("");
  const [saving, setSaving] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [newComment, setNewComment] = useState("");
  const [posting, setPosting] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editBody, setEditBody] = useState("");

  useEffect(() => {
    if (!token) return;
    let active = true;
    apiClient<CardDetail>(`/api/cards/${cardId}`, token)
      .then((res) => {
        if (!active) return;
        setCard(res);
        setTitle(res.title);
        setDescription(res.description ?? "");
        setAssigneeId(res.assignee_id ?? "");
      })
      .catch((err) => {
        if (!active) return;
        handleError(err);
        onClose();
      });
    return () => {
      active = false;
    };
    // onClose identity is not a reason to refetch.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cardId, token, handleError]);

  const save = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const updated = await apiClient<Card>(`/api/cards/${cardId}`, token, {
        method: "PATCH",
        body: JSON.stringify({
          title: title.trim(),
          description: description.trim() ? description : null,
          assignee_id: assigneeId || null,
        }),
      });
      setCard((prev) => (prev ? { ...prev, ...updated } : prev));
      onUpdated(updated);
      toast.success("Card saved");
    } catch (err) {
      handleError(err);
    } finally {
      setSaving(false);
    }
  };

  const deleteCard = async () => {
    setDeleting(true);
    try {
      await apiClient<{ id: string }>(`/api/cards/${cardId}`, token, { method: "DELETE" });
      onDeleted(cardId);
      onClose();
    } catch (err) {
      handleError(err);
      setDeleting(false);
    }
  };

  const postComment = async (e: FormEvent) => {
    e.preventDefault();
    setPosting(true);
    try {
      const comment = await apiClient<Comment>(`/api/cards/${cardId}/comments`, token, {
        method: "POST",
        body: JSON.stringify({ body: newComment.trim() }),
      });
      setCard((prev) => (prev ? { ...prev, comments: [...prev.comments, comment] } : prev));
      setNewComment("");
    } catch (err) {
      handleError(err);
    } finally {
      setPosting(false);
    }
  };

  const saveComment = async (id: string) => {
    try {
      const updated = await apiClient<Comment>(`/api/comments/${id}`, token, {
        method: "PATCH",
        body: JSON.stringify({ body: editBody.trim() }),
      });
      setCard((prev) =>
        prev ? { ...prev, comments: prev.comments.map((c) => (c.id === id ? updated : c)) } : prev,
      );
      setEditingId(null);
    } catch (err) {
      handleError(err);
    }
  };

  const deleteComment = async (id: string) => {
    try {
      await apiClient<{ id: string }>(`/api/comments/${id}`, token, { method: "DELETE" });
      setCard((prev) => (prev ? { ...prev, comments: prev.comments.filter((c) => c.id !== id) } : prev));
    } catch (err) {
      handleError(err);
    }
  };

  return (
    <>
      <BaseModal
        isOpen={!confirmDelete}
        title="Card details"
        onClose={onClose}
      >
        {card === null ? (
          <p className="text-gray-500">Loading…</p>
        ) : (
          <div className="space-y-6">
            <form onSubmit={save} className="space-y-3">
              <div className="flex items-center gap-2">
                <BaseBadge tone={card.completed_at ? "success" : "neutral"}>
                  {card.completed_at ? "Done" : "Open"}
                </BaseBadge>
              </div>
              <label className="block text-sm font-medium text-gray-700">
                Title
                <input
                  required
                  maxLength={200}
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className={FIELD}
                />
              </label>
              <label className="block text-sm font-medium text-gray-700">
                Description
                <textarea
                  rows={4}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className={FIELD}
                />
              </label>
              <label className="block text-sm font-medium text-gray-700">
                Assignee
                <select value={assigneeId} onChange={(e) => setAssigneeId(e.target.value)} className={FIELD}>
                  <option value="">Unassigned</option>
                  {members.map((m) => (
                    <option key={m.user_id} value={m.user_id}>
                      {m.name}
                    </option>
                  ))}
                </select>
              </label>
              <div className="flex justify-between gap-2">
                <BaseButton variant="destructive" onClick={() => setConfirmDelete(true)}>
                  Delete card
                </BaseButton>
                <BaseButton type="submit" loading={saving} disabled={!title.trim()}>
                  Save
                </BaseButton>
              </div>
            </form>

            <section aria-label="Comments" className="space-y-3">
              <h3 className="text-sm font-semibold text-gray-900">Comments ({card.comments.length})</h3>
              <ul className="space-y-3">
                {card.comments.map((c) => {
                  const own = c.author_id === user?.id;
                  return (
                    <li key={c.id} className="rounded-md bg-gray-50 p-3 text-sm">
                      <div className="mb-1 flex items-center justify-between gap-2 text-xs text-gray-500">
                        <span className="font-medium text-gray-700">{c.author_name}</span>
                        <span>{new Date(c.created_at).toLocaleString()}</span>
                      </div>
                      {editingId === c.id ? (
                        <div className="space-y-2">
                          <textarea
                            rows={3}
                            maxLength={2000}
                            value={editBody}
                            onChange={(e) => setEditBody(e.target.value)}
                            aria-label="Edit comment"
                            className={FIELD}
                          />
                          <div className="flex justify-end gap-2">
                            <BaseButton variant="secondary" onClick={() => setEditingId(null)}>
                              Cancel
                            </BaseButton>
                            <BaseButton disabled={!editBody.trim()} onClick={() => saveComment(c.id)}>
                              Save
                            </BaseButton>
                          </div>
                        </div>
                      ) : (
                        <>
                          <p className="whitespace-pre-wrap break-words text-gray-900">{c.body}</p>
                          {own && (
                            <div className="mt-2 flex justify-end gap-2">
                              <BaseButton
                                variant="secondary"
                                onClick={() => {
                                  setEditingId(c.id);
                                  setEditBody(c.body);
                                }}
                              >
                                Edit
                              </BaseButton>
                              <BaseButton variant="destructive" onClick={() => deleteComment(c.id)}>
                                Delete
                              </BaseButton>
                            </div>
                          )}
                        </>
                      )}
                    </li>
                  );
                })}
              </ul>
              <form onSubmit={postComment} className="space-y-2">
                <textarea
                  rows={3}
                  maxLength={2000}
                  value={newComment}
                  onChange={(e) => setNewComment(e.target.value)}
                  placeholder="Write a comment…"
                  aria-label="New comment"
                  className={FIELD}
                />
                <div className="flex justify-end">
                  <BaseButton type="submit" loading={posting} disabled={!newComment.trim()}>
                    Post comment
                  </BaseButton>
                </div>
              </form>
            </section>
          </div>
        )}
      </BaseModal>
      <BaseModal
        isOpen={confirmDelete}
        title="Delete card?"
        onClose={() => setConfirmDelete(false)}
        footer={
          <>
            <BaseButton variant="secondary" onClick={() => setConfirmDelete(false)}>
              Cancel
            </BaseButton>
            <BaseButton variant="destructive" loading={deleting} onClick={deleteCard}>
              Delete
            </BaseButton>
          </>
        }
      >
        <p className="text-sm text-gray-700">This card and its comments will be removed.</p>
      </BaseModal>
    </>
  );
}
